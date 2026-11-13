"""GSM8K 测试集上比较 GRPO 前后格式与答案，不使用训练样本。"""
import argparse
import json
import re
from pathlib import Path
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from train import SYSTEM_PROMPT, extract_hash_answer

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / 'PPO/Qwen2.5-0.5B-Instruct'


def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',default=str(ROOT/'outputs/Qwen2.5-0.5B-reasoning-GRPO')); p.add_argument('--samples',type=int,default=64); p.add_argument('--max-new-tokens',type=int,default=128); p.add_argument('--batch-size',type=int,default=4); p.add_argument('--output',default=str(ROOT/'evaluation_grpo.json')); a=p.parse_args()
    tok=AutoTokenizer.from_pretrained(BASE,local_files_only=True,padding_side='left'); tok.pad_token=tok.eos_token
    data=load_dataset('parquet',data_files=str(ROOT/'gsm8k/test.parquet'),split='train').shuffle(seed=42).select(range(a.samples))
    prompts=[tok.apply_chat_template([{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':x}],tokenize=False,add_generation_prompt=True) for x in data['question']]
    results={'test_split':'GSM8K test','samples':a.samples,'seed':42,'generation':{'do_sample':False,'max_new_tokens':a.max_new_tokens},'models':{}}
    for name,path in [('base',str(BASE)),('grpo',a.model)]:
        model=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,local_files_only=True).to('cuda').eval()
        correct=formatted=0; examples=[]
        for i in range(0,len(prompts),a.batch_size):
            x=tok(prompts[i:i+a.batch_size],return_tensors='pt',padding=True).to('cuda')
            with torch.inference_mode(): y=model.generate(**x,max_new_tokens=a.max_new_tokens,do_sample=False,pad_token_id=tok.pad_token_id,temperature=None,top_p=None,top_k=None)
            outputs=tok.batch_decode(y[:,x['input_ids'].shape[1]:],skip_special_tokens=True)
            for j,text in enumerate(outputs):
                match=re.search(r'<answer>\s*(.*?)\s*</answer>',text,re.DOTALL); extracted=match.group(1).strip().replace(',','') if match else None
                target=extract_hash_answer(data[i+j]['answer']).replace(',','')
                formatted+=bool(match); correct+= extracted==target
                if len(examples)<3: examples.append({'question':data[i+j]['question'],'target':target,'response':text})
        results['models'][name]={'exact_answer_accuracy':correct/a.samples,'answer_tag_rate':formatted/a.samples,'examples':examples}
        print(name,'accuracy',correct/a.samples,'answer_tag_rate',formatted/a.samples,flush=True)
        del model; torch.cuda.empty_cache()
    Path(a.output).write_text(json.dumps(results,ensure_ascii=False,indent=2)); print('保存结果:',a.output)
if __name__=='__main__':main()
