"""单卡 LoRA SFT 教学示例：仅对 assistant 回答计算 loss。"""
import argparse
import json
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).resolve().parent


class SFTDataset(Dataset):
    def __init__(self, file_path, tokenizer, max_length, limit):
        self.examples = []
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                if len(self.examples) >= limit:
                    break
                item = json.loads(line)
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": item["query"]},
                ]
                prefix = tokenizer.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=True
                )
                full = tokenizer.apply_chat_template(
                    messages + [{"role": "assistant", "content": item["answer"]}],
                    tokenize=True, add_generation_prompt=False,
                )
                if full[:len(prefix)] != prefix:
                    raise ValueError("对话模板前缀不匹配，无法安全地屏蔽问题部分")
                full = full[:max_length]
                if len(full) <= len(prefix):
                    continue
                self.examples.append({
                    "input_ids": full,
                    "labels": [-100] * len(prefix) + full[len(prefix):],
                })
        if not self.examples:
            raise ValueError("没有有效样本：请检查数据或增大 max_length")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, index):
        return self.examples[index]


def collate(batch, pad_id):
    length = max(len(item["input_ids"]) for item in batch)
    input_ids, labels, attention_mask = [], [], []
    for item in batch:
        n = len(item["input_ids"])
        input_ids.append(item["input_ids"] + [pad_id] * (length - n))
        labels.append(item["labels"] + [-100] * (length - n))
        attention_mask.append([1] * n + [0] * (length - n))
    return {"input_ids": torch.tensor(input_ids), "labels": torch.tensor(labels),
            "attention_mask": torch.tensor(attention_mask)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="/home/leon/Model/ModelScope/Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--data", default=str(HERE / "data/sft_data.json"))
    parser.add_argument("--output", default=str(HERE / "output_lora"))
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    args = parser.parse_args()
    if args.limit <= 0 or args.steps <= 0 or args.batch_size <= 0:
        parser.error("limit、steps 和 batch-size 必须大于零")
    torch.manual_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    dataset = SFTDataset(args.data, tokenizer, args.max_length, args.limit)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False,
                        collate_fn=lambda b: collate(b, tokenizer.pad_token_id))
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=dtype, local_files_only=True
    ).to(device)
    config = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
                        target_modules=["q_proj", "v_proj"],
                        task_type=TaskType.CAUSAL_LM, bias="none")
    model = get_peft_model(model, config)
    model.config.use_cache = False
    model.print_trainable_parameters()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    model.train()
    iterator = iter(loader)
    for step in range(args.steps):
        try:
            batch = next(iterator)
        except StopIteration:
            iterator = iter(loader)
            batch = next(iterator)
        batch = {k: v.to(device) for k, v in batch.items()}
        optimizer.zero_grad(set_to_none=True)
        loss = model(**batch).loss
        if not torch.isfinite(loss):
            raise ValueError("loss 不是有限值，已停止训练")
        loss.backward()
        optimizer.step()
        print(f"step {step + 1}/{args.steps} loss={loss.item():.4f} "
              f"监督 token={int((batch['labels'] != -100).sum().item())}", flush=True)
    model.save_pretrained(args.output)
    print(f"LoRA adapter 已保存至: {args.output}")


if __name__ == "__main__":
    main()
