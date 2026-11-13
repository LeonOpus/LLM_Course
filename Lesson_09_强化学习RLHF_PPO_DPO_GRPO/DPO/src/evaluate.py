"""独立 DPO 测试集：比较原模型和训练模型对偏好对的评分。"""
import json
from pathlib import Path
import torch
from datasets import load_dataset
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer
from train import ROOT, collate_fn, logps

base=ROOT/'src/Qwen2.5-0.5B-Instruct'; trained=ROOT/'model-DPO-local'; device='cuda'
tok=AutoTokenizer.from_pretrained(base,local_files_only=True); tok.pad_token=tok.eos_token
data=load_dataset('parquet',data_files=str(ROOT/'src/truthy-dpo-v0.1/truthy-dpo.parquet'),split='train').train_test_split(test_size=.1,seed=2003)['test'].select(range(64))
loader=DataLoader(data,batch_size=1,shuffle=False,collate_fn=lambda xs:collate_fn(xs,tok,192,device))
scores={}
for name,path in [('base',base),('dpo',trained)]:
 model=AutoModelForCausalLM.from_pretrained(path,torch_dtype=torch.bfloat16,local_files_only=True).to(device).eval(); values=[]
 with torch.inference_mode():
  for batch in loader: values.extend((logps(model,batch,'chosen')-logps(model,batch,'rejected')).float().cpu().tolist())
 scores[name]=values; del model; torch.cuda.empty_cache()
print('测试偏好对:',len(data))
for key,val in scores.items(): print(key,'绝对偏好正确率',round(sum(v>0 for v in val)/len(val),4),'平均差值',round(sum(val)/len(val),4))
changes=[x-y for x,y in zip(scores['dpo'],scores['base'])]
print('相对参考模型偏好差值改善比例',round(sum(v>0 for v in changes)/len(changes),4),'平均变化',round(sum(changes)/len(changes),4))
Path(ROOT/'evaluation_dpo.json').write_text(json.dumps({'samples':len(data),'seed':2003,'absolute_accuracy':{k:sum(v>0 for v in vals)/len(vals) for k,vals in scores.items()},'relative_improvement_fraction':sum(v>0 for v in changes)/len(changes),'relative_margin_change':sum(changes)/len(changes)},indent=2))
