"""在独立 IMDB 测试集上比较课程 PPO 权重与原始模型的情绪评分。"""
import argparse
import json
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoModelForSequenceClassification, AutoTokenizer

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--samples', type=int, default=32)
    ap.add_argument('--max-new-tokens', type=int, default=48)
    ap.add_argument('--batch-size', type=int, default=4)
    ap.add_argument('--output', default=str(HERE / 'evaluation_sentiment.json'))
    args = ap.parse_args()
    if min(args.samples, args.max_new_tokens, args.batch_size) <= 0:
        ap.error('样本数、长度和批次必须大于零')
    base = HERE / 'Qwen2.5-0.5B-Instruct'
    paths = {'base': base, 'course_ppo': HERE / 'qwen_ppo_sentiment_final'}
    tok = AutoTokenizer.from_pretrained(base, local_files_only=True, padding_side='left')
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    dataset = load_dataset('parquet', data_files=str(HERE / 'imdb/plain_text/test-00000-of-00001.parquet'), split='train')
    dataset = dataset.filter(lambda x: len(x['text']) > 100).shuffle(seed=42).select(range(args.samples))
    snippets = [tok.decode(tok(t, add_special_tokens=False).input_ids[:10], skip_special_tokens=True) for t in dataset['text']]
    prompts = [tok.apply_chat_template([
        {'role': 'system', 'content': 'You are a helpful assistant that continues to finish writing English movie reviews.'},
        {'role': 'user', 'content': 'Continue to write the following English movie review snippet:\n\n' + s}],
        tokenize=False, add_generation_prompt=True) for s in snippets]
    reward_path = HERE / 'distilbert'
    rtok = AutoTokenizer.from_pretrained(reward_path, local_files_only=True)
    reward = AutoModelForSequenceClassification.from_pretrained(reward_path, local_files_only=True).to('cuda').eval()
    pos = next(k for k, v in reward.config.id2label.items() if v.upper() == 'POSITIVE')
    results = {'test_split': 'IMDB test', 'samples': args.samples, 'seed': 42,
               'generation': {'do_sample': False, 'max_new_tokens': args.max_new_tokens}, 'models': {}}
    for name, model_path in paths.items():
        model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, torch_dtype=torch.bfloat16).to('cuda').eval()
        scores, continuation_scores, examples = [], [], []
        for offset in range(0, len(prompts), args.batch_size):
            batch = prompts[offset:offset + args.batch_size]
            x = tok(batch, return_tensors='pt', padding=True).to('cuda')
            with torch.inference_mode():
                y = model.generate(**x, max_new_tokens=args.max_new_tokens, do_sample=False,
                                   pad_token_id=tok.pad_token_id, temperature=None, top_p=None, top_k=None)
            responses = tok.batch_decode(y[:, x['input_ids'].shape[1]:], skip_special_tokens=True)
            for texts, out in (([a + b for a, b in zip(batch, responses)], scores), (responses, continuation_scores)):
                r = rtok(texts, return_tensors='pt', padding=True, truncation=True, max_length=512).to('cuda')
                with torch.inference_mode(): out.extend(reward(**r).logits.softmax(-1)[:, pos].float().cpu().tolist())
            for snippet, response in zip(snippets[offset:offset + len(batch)], responses):
                if len(examples) < 3: examples.append({'prompt': snippet, 'response': response})
        results['models'][name] = {'positive_mean_prompt_plus_response': sum(scores)/len(scores),
                                   'positive_mean_response_only': sum(continuation_scores)/len(continuation_scores),
                                   'positive_fraction_response_only': sum(x >= .5 for x in continuation_scores)/len(continuation_scores),
                                   'examples': examples}
        print(name, json.dumps(results['models'][name], ensure_ascii=False), flush=True)
        del model
        torch.cuda.empty_cache()
    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print('结果已保存:',args.output)

if __name__ == '__main__':
    main()
