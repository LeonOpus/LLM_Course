"""强制选择 PyTorch SDPA 数学/Flash 后端，比较结果与单卡耗时。"""
import json
from pathlib import Path
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel, SDPBackend

def main():
    if not torch.cuda.is_available(): raise RuntimeError('本实验需要 CUDA')
    torch.manual_seed(42)
    shape=(1,8,512,64)
    q,k,v=[torch.randn(shape,device='cuda',dtype=torch.float16) for _ in range(3)]
    output={}
    tensors={}
    for name,backend in [('math',SDPBackend.MATH),('flash',SDPBackend.FLASH_ATTENTION)]:
        with sdpa_kernel(backend):
            for _ in range(10): y=F.scaled_dot_product_attention(q,k,v,is_causal=True,dropout_p=0.0)
            torch.cuda.synchronize(); start=torch.cuda.Event(enable_timing=True); end=torch.cuda.Event(enable_timing=True); start.record()
            for _ in range(100): y=F.scaled_dot_product_attention(q,k,v,is_causal=True,dropout_p=0.0)
            end.record(); torch.cuda.synchronize(); output[name]={'mean_ms':start.elapsed_time(end)/100}; tensors[name]=y
    output['max_abs_diff']=float((tensors['math']-tensors['flash']).abs().max()); output['mean_abs_diff']=float((tensors['math']-tensors['flash']).abs().mean()); output['shape']=shape; output['dtype']='float16'; output['causal']=True
    Path(__file__).with_name('attention_benchmark_result.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(output,ensure_ascii=False))
if __name__=='__main__':main()
