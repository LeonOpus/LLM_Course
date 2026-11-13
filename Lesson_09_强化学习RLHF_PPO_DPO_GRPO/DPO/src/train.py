"""Qwen 偏好对 DPO：仅对回答 token 计算因果对数概率。"""
import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from datasets import load_dataset
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]


def calculate_DPO_loss(model_preferred_logprob, model_dispreferred_logprob,
                       ref_preferred_logprob, ref_dispreferred_logprob, beta=0.1):
    preferred = model_preferred_logprob - ref_preferred_logprob
    rejected = model_dispreferred_logprob - ref_dispreferred_logprob
    margin = preferred - rejected
    return -F.logsigmoid(beta * margin).mean(), (margin > 0).float().mean(), margin.mean()


def get_log_prob(logits, labels):
    """模型位置 t 预测标签 t+1；-100 标记 prompt 和 padding。"""
    logits = logits[:, :-1, :].float()
    labels = labels[:, 1:]
    mask = labels.ne(-100)
    if not mask.any(dim=1).all():
        raise ValueError('存在没有有效回答 token 的样本')
    selected = F.log_softmax(logits, dim=-1).gather(-1, labels.masked_fill(~mask, 0).unsqueeze(-1)).squeeze(-1)
    return (selected * mask).sum(dim=-1)


def collate_fn(batch, tokenizer, max_length, device):
    def build(item, response_key):
        # 每对样本共用相同 prompt，分别拼接回答，右填充避免中间插入 padding。
        prompt = tokenizer('Instruct: ' + item['prompt'] + '\nOutput: ', add_special_tokens=False).input_ids
        answer = tokenizer(item[response_key], add_special_tokens=False).input_ids
        prompt = prompt[:max_length // 2]
        answer = answer[:max_length - len(prompt) - 1]
        if not answer:
            raise ValueError('回答为空或被截断')
        ids = prompt + answer + [tokenizer.eos_token_id]
        return ids, [-100] * len(prompt) + answer + [tokenizer.eos_token_id]

    result = {}
    for prefix, key in [('chosen', 'chosen'), ('rejected', 'rejected')]:
        rows = [build(item, key) for item in batch]
        length = max(len(ids) for ids, _ in rows)
        result[prefix + '_ids'] = torch.tensor([ids + [tokenizer.pad_token_id] * (length-len(ids)) for ids, _ in rows], device=device)
        result[prefix + '_labels'] = torch.tensor([labs + [-100] * (length-len(labs)) for ids, labs in rows], device=device)
        result[prefix + '_mask'] = torch.tensor([[1] * len(ids) + [0] * (length-len(ids)) for ids, _ in rows], device=device)
    return result


def logps(model, batch, key):
    logits = model(input_ids=batch[key+'_ids'], attention_mask=batch[key+'_mask'], use_cache=False).logits
    return get_log_prob(logits, batch[key+'_labels'])


@torch.no_grad()
def evaluate(model, ref_model, loader, beta):
    model.eval(); margins = []; losses = []
    for batch in loader:
        chosen = logps(model, batch, 'chosen'); rejected = logps(model, batch, 'rejected')
        ref_chosen = logps(ref_model, batch, 'chosen'); ref_rejected = logps(ref_model, batch, 'rejected')
        relative = (chosen - ref_chosen) - (rejected - ref_rejected)
        margins.extend(relative.float().cpu().tolist())
        losses.extend((-F.logsigmoid(beta * relative)).float().cpu().tolist())
    model.train()
    return {'examples': len(margins), 'loss': float(np.mean(losses)),
            'relative_margin': float(np.mean(margins)),
            'relative_preference_accuracy': float(np.mean(np.array(margins) > 0))}


def main():
    ap = argparse.ArgumentParser(description='DPO 偏好训练及独立验证')
    ap.add_argument('--model_name', default=str(ROOT / 'src/Qwen2.5-0.5B-Instruct'))
    ap.add_argument('--dataset_name', default=str(ROOT / 'src/truthy-dpo-v0.1/truthy-dpo.parquet'))
    ap.add_argument('--output_dir', default=str(ROOT / 'model-DPO-local'))
    ap.add_argument('--epochs', type=int, default=1)
    ap.add_argument('--max_steps', type=int, default=100)
    ap.add_argument('--eval_samples', type=int, default=64)
    ap.add_argument('--beta', type=float, default=0.1)
    ap.add_argument('--batch_size', type=int, default=1)
    ap.add_argument('--gradient_accumulation_steps', type=int, default=4)
    ap.add_argument('--max_length', type=int, default=192)
    ap.add_argument('--lr', type=float, default=1e-6)
    ap.add_argument('--seed', type=int, default=2003)
    args = ap.parse_args()
    if min(args.epochs,args.max_steps,args.eval_samples,args.batch_size,args.gradient_accumulation_steps) <= 0 or args.max_length < 8:
        ap.error('训练参数必须大于零，max_length 至少为 8')
    torch.manual_seed(args.seed); np.random.seed(args.seed); random.seed(args.seed)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    tok = AutoTokenizer.from_pretrained(args.model_name, local_files_only=True)
    tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if device.type == 'cuda' and torch.cuda.is_bf16_supported() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=dtype, local_files_only=True).to(device)
    ref = AutoModelForCausalLM.from_pretrained(args.model_name, torch_dtype=dtype, local_files_only=True).to(device).eval()
    ref.requires_grad_(False); model.config.use_cache = False
    data = load_dataset('parquet', data_files=args.dataset_name, split='train').train_test_split(test_size=0.1, seed=args.seed)
    test = data['test'].select(range(min(args.eval_samples, len(data['test']))))
    collate = lambda x: collate_fn(x, tok, args.max_length, device)
    train_loader = DataLoader(data['train'], batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    eval_loader = DataLoader(test, batch_size=args.batch_size, shuffle=False, collate_fn=collate)
    optimizer = AdamW(model.parameters(), lr=args.lr)
    before = evaluate(model, ref, eval_loader, args.beta); print('训练前验证:', before, flush=True)
    step = micro = 0
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(args.epochs):
        for i, batch in enumerate(train_loader):
            with torch.no_grad(): rc = logps(ref,batch,'chosen'); rr = logps(ref,batch,'rejected')
            c = logps(model,batch,'chosen'); r = logps(model,batch,'rejected')
            loss, accuracy, margin = calculate_DPO_loss(c,r,rc,rr,args.beta)
            if not torch.isfinite(loss): raise ValueError('loss 非有限值')
            (loss / args.gradient_accumulation_steps).backward(); micro += 1
            if micro == args.gradient_accumulation_steps or i + 1 == len(train_loader):
                if micro != args.gradient_accumulation_steps:
                    for p in model.parameters():
                        if p.grad is not None: p.grad.mul_(args.gradient_accumulation_steps / micro)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step(); optimizer.zero_grad(set_to_none=True); micro = 0; step += 1
                if step % 10 == 0 or step == 1:
                    print(f'更新 {step}/{args.max_steps} loss={loss.item():.4f} margin={margin.item():.4f}',flush=True)
                if step >= args.max_steps: break
        if step >= args.max_steps: break
    after = evaluate(model, ref, eval_loader, args.beta); print('训练后验证:', after, flush=True)
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out); tok.save_pretrained(out)
    (out/'evaluation.json').write_text(json.dumps({'seed':args.seed,'steps':step,'before':before,'after':after},ensure_ascii=False,indent=2))
    print('模型与验证指标已保存:',out,flush=True)


if __name__ == '__main__':
    main()
