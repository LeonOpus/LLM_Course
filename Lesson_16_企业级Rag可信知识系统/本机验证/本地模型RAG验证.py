"""用真实本地 BGE-M3、Qwen 及隔离 Milvus 集合验证 RAG；不调用云接口。"""
import json,os,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'RAG参考实现'/'backend'))
from fastapi.testclient import TestClient
from rag_app.config import Settings
from rag_app.main import create_app
from rag_app.providers import Bailian
from rag_app.vectorstore import VectorStore
from rag_app.generation import build_messages,validate_answer
python='/home/leon/miniconda3/envs/llm-course/bin/python'
embedding_code=r'''
import json,sys,torch
from transformers import AutoTokenizer,AutoModel
texts=json.load(sys.stdin);path='/home/leon/Model/ModelScope/BAAI/bge-m3'
t=AutoTokenizer.from_pretrained(path,local_files_only=True);m=AutoModel.from_pretrained(path,local_files_only=True,torch_dtype=torch.float16).cuda().eval()
x=t(texts,padding=True,truncation=True,max_length=512,return_tensors='pt').to('cuda')
with torch.inference_mode(): v=torch.nn.functional.normalize(m(**x).last_hidden_state[:,0].float(),p=2,dim=1)
print(json.dumps(v.cpu().tolist()))
'''
generation_code=r'''
import json,os,sys,torch
from transformers import AutoTokenizer,AutoModelForCausalLM
msgs=json.load(sys.stdin);path=os.environ.get('L16_LOCAL_MODEL','/home/leon/Model/ModelScope/Qwen/Qwen2.5-7B-Instruct')
t=AutoTokenizer.from_pretrained(path,local_files_only=True);m=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,torch_dtype=torch.bfloat16).cuda().eval()
x=t.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True,return_tensors='pt').to('cuda')
with torch.inference_mode(): out=m.generate(x,attention_mask=torch.ones_like(x),max_new_tokens=256,do_sample=False,pad_token_id=t.eos_token_id)
eos=m.generation_config.eos_token_id
eos=[eos] if isinstance(eos,int) else (eos or [])
print(json.dumps({'text':t.decode(out[0,x.shape[1]:],skip_special_tokens=True),'finish_reason':'stop' if out[0,-1].item() in eos else 'length'},ensure_ascii=False))
'''
def run_model(code,inputs):
    p=subprocess.run([python,'-c',code],input=json.dumps(inputs,ensure_ascii=False),text=True,capture_output=True,timeout=120)
    if p.returncode:raise RuntimeError('本机模型执行失败: '+p.stderr[-1500:])
    return json.loads(p.stdout.strip().splitlines()[-1])
def embed(_self,texts):return run_model(embedding_code,texts)
def answer(_self,query,hits,history=None):
    if not hits:return _self._empty_answer()
    generated=run_model(generation_code,build_messages(query,hits,history))
    output=generated['text']
    try:return validate_answer(output,hits,finish_reason=generated['finish_reason'])
    except ValueError as e:
        print('本机模型输出未通过原项目引用格式校验:',output[:500],flush=True)
        raise RuntimeError('本机模型输出未通过原项目引用格式校验') from e
collection='rag_course_local_'+uuid4().hex[:12]
source=root/'RAG实操课程'/'02-知识库资料'/'工单记录与咨询'/'D34-售后工单记录.csv'
with tempfile.TemporaryDirectory(prefix='lesson16-real-') as temp:
    model_name=Path(os.environ.get('L16_LOCAL_MODEL','/home/leon/Model/ModelScope/Qwen/Qwen2.5-7B-Instruct')).name
    settings=Settings(_env_file=None,runtime_dir=Path(temp),milvus_collection=collection,embedding_model='local-bge-m3',embedding_dim=1024,chat_model=model_name,dashscope_api_key='')
    store=VectorStore(settings)
    if store.client.has_collection(collection):raise RuntimeError('集合意外存在')
    try:
        with patch.object(Bailian,'embed',embed),patch.object(Bailian,'answer',answer),TestClient(create_app(settings)) as client:
            with source.open('rb') as f:r=client.post('/api/documents',files={'file':(source.name,f,'text/csv')})
            r.raise_for_status();did=r.json()['doc_id'];client.post(f'/api/documents/{did}/parse').raise_for_status()
            r=client.post(f'/api/documents/{did}/index');r.raise_for_status()
            doc=next(x for x in client.get('/api/documents').json() if x['doc_id']==did)
            if doc['status']!='ready':raise RuntimeError('本地 BGE 入库未成功: '+str(doc.get('error')))
            q='WO-004 工单的设备型号是什么？'
            result=client.post('/api/ask',json={'question':q,'top_k':5,'final_k':5})
            if not result.is_success:
                print('BGE-M3 已完成真实向量入库；问答失败:',result.status_code,result.json(),flush=True)
                result.raise_for_status()
            data=result.json()
            print('BGE-M3 入库块数:',doc['chunk_count'],'Milvus 候选数:',len(data['trace']['candidates']))
            print('Qwen回答:',data['answer']);print('状态:',data['status'],'引用数:',len(data['citations']))
            print('引用编号检查:',data['validation']['citation_membership'],'语义支持:',data['validation']['semantic_support'])
            print('回答含S10:', 'S10' in data['answer'], '引用中含对应工单和型号:',any('WO-004' in c.get('text','') and 'S10' in c.get('text','') for c in data['citations']))
            print('真实答案为 S10；单条样本仅验证链路，不是质量评估。')
    finally:
        if store.client.has_collection(collection):store.client.drop_collection(collection)
        store.client.close()
