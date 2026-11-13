"""真实 Milvus + 确定性测试向量：验证链路，不能评估语义检索质量。"""
import hashlib
import sys
import tempfile
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

collection='rag_course_smoke_'+uuid4().hex[:12]
def fake_embedding(_self,texts):
    vectors=[]
    for text in texts:
        digest=hashlib.sha256(text.encode('utf8')).digest()
        vectors.append([(digest[i]-127.5)/127.5 for i in range(16)])
    return vectors
with tempfile.TemporaryDirectory(prefix='lesson16-smoke-') as runtime:
    settings=Settings(_env_file=None,runtime_dir=Path(runtime),milvus_collection=collection,
                      embedding_model='deterministic-test-only',embedding_dim=16,dashscope_api_key='')
    store=VectorStore(settings)
    if store.client.has_collection(collection): raise RuntimeError('测试集合意外已存在，停止')
    try:
        with patch.object(Bailian,'embed',fake_embedding), TestClient(create_app(settings)) as client:
            sample='工单编号,设备型号,情况\nTEST-001,X200,振动异常\nTEST-002,X100,例行检查\n'.encode('utf8')
            uploaded=client.post('/api/documents',files={'file':('demo.csv',sample,'text/csv')});uploaded.raise_for_status();doc_id=uploaded.json()['doc_id']
            parsed=client.post(f'/api/documents/{doc_id}/parse');parsed.raise_for_status()
            preview=client.get(f'/api/documents/{doc_id}/chunks');preview.raise_for_status();chunks=preview.json()['chunks'];assert len(chunks)==2
            indexed=client.post(f'/api/documents/{doc_id}/index');indexed.raise_for_status()
            item=next(d for d in client.get('/api/documents').json() if d['doc_id']==doc_id);assert item['status']=='ready',item
            result=client.post('/api/retrieve',json={'question':chunks[0]['text'],'top_k':2});result.raise_for_status();data=result.json()
            assert data['mode']=='live' and data['candidates'][0]['chunk_id']==chunks[0]['chunk_id']
            print('真实 Milvus：上传 → CSV 解析 → 2 个块 → 入库 → 检索成功')
            print('top1 匹配原文:',data['candidates'][0]['text']==chunks[0]['text'],'来源:',data['candidates'][0]['locator'])
            print('向量是本地确定性测试替身；查询使用片段原文，不代表语义检索准确率。')
    finally:
        if store.client.has_collection(collection):store.client.drop_collection(collection)
        store.client.close()
