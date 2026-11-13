"""本地 Qwen 的 BF16、INT8、NF4 量化内存及生成对比。"""
import argparse
import gc
import json
import time
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model',default='/home/leon/Model/ModelScope/Qwen/Qwen2.5-1.5B-Instruct'); ap.add_argument('--output',default=str(Path(__file__).resolve().parent/'quantization_benchmark_result.json')); ap.add_argument('--runs',type=int,default=3); ap.add_argument('--max-new-tokens',type=int,default=64); args=ap.parse_args()
    if args.runs < 1 or args.max_new_tokens < 1: ap.error('runs 与 max-new-tokens 必须大于零')
    if not torch.cuda.is_available(): raise RuntimeError('本实验需要 CUDA')
    tokenizer=AutoTokenizer.from_pretrained(args.model,local_files_only=True)
    messages=[{'role':'user','content':'请用两句话解释 KV Cache 的作用。'}]
    inputs=tokenizer.apply_chat_template(messages,add_generation_prompt=True,tokenize=True,return_tensors='pt').to('cuda')
    outputs={}
    for mode in ('bf16','int8','nf4'):
        gc.collect(); torch.cuda.empty_cache(); baseline=torch.cuda.memory_allocated(); torch.cuda.reset_peak_memory_stats()
        opts={'torch_dtype':torch.bfloat16,'device_map':{'':'cuda:0'},'local_files_only':True}
        if mode=='int8': opts['quantization_config']=BitsAndBytesConfig(load_in_8bit=True)
        if mode=='nf4': opts['quantization_config']=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
        model=AutoModelForCausalLM.from_pretrained(args.model,**opts).eval()
        torch.cuda.synchronize(); model_alloc=torch.cuda.memory_allocated()-baseline
        kwargs={'max_new_tokens':args.max_new_tokens,'min_new_tokens':args.max_new_tokens,'do_sample':False,'pad_token_id':tokenizer.eos_token_id,'attention_mask':torch.ones_like(inputs)}
        with torch.inference_mode():
            model.generate(inputs,**kwargs)
            durations=[]
            for _ in range(args.runs):
                torch.cuda.synchronize(); t=time.perf_counter(); generated=model.generate(inputs,**kwargs); torch.cuda.synchronize(); durations.append(time.perf_counter()-t)
        text=tokenizer.decode(generated[0,inputs.shape[1]:],skip_special_tokens=True)
        outputs[mode]={'gpu_allocated_model_gib':model_alloc/1024**3,'gpu_peak_gib':(torch.cuda.max_memory_allocated()-baseline)/1024**3,'generated_tokens':args.max_new_tokens,'seconds':durations,'average_tokens_per_second':args.max_new_tokens/(sum(durations)/len(durations)),'response':text}
        print(mode,json.dumps(outputs[mode],ensure_ascii=False),flush=True)
        del model,generated; gc.collect(); torch.cuda.empty_cache()
    Path(args.output).write_text(json.dumps({'model':args.model,'input_tokens':int(inputs.shape[1]),'runs':args.runs,'results':outputs},ensure_ascii=False,indent=2))
    print('结果已保存:',args.output)
if __name__=='__main__': main()
