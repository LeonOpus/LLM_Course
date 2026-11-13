from hashlib import sha256
from pathlib import Path
import json
import re
import shutil
from uuid import uuid4
from fastapi import FastAPI,UploadFile,File,HTTPException,BackgroundTasks
from fastapi.responses import FileResponse,JSONResponse,StreamingResponse
from starlette.concurrency import run_in_threadpool
from typing import Literal
import anyio
from rag_app.generation import build_messages
from pydantic import BaseModel,Field,field_validator,model_validator
from rag_app.providers import ProviderError
from rag_app.vectorstore import VectorStore
from rag_app.config import Settings
from rag_app.storage import Store
from rag_app.pipeline import Pipeline
from rag_app.health import public_health

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
KINDS={'.pdf':'pdf','.docx':'docx','.doc':'docx','.xlsx':'xlsx','.xls':'xlsx','.pptx':'pptx','.ppt':'pptx',
       '.png':'image','.jpg':'image','.jpeg':'image','.bmp':'image','.tif':'image','.tiff':'image',
       '.html':'html','.htm':'html','.md':'md','.txt':'txt','.csv':'csv'}
MAX_BYTES=50*1024*1024

class RetrieveRequest(BaseModel):
    question:str=Field(min_length=1,max_length=2000)
    top_k:int=Field(default=10,ge=1,le=50,strict=True)
    doc_ids:list[str]|None=None
    @field_validator('question')
    @classmethod
    def clean_question(cls,value):
        if not value.strip():raise ValueError('问题不能为空')
        return value.strip()

class AskRequest(RetrieveRequest):
    strategy:Literal['baseline','rerank']='baseline'
    final_k:int=Field(default=5,ge=1,le=20,strict=True)
    history:list[dict[str,str]]=Field(default_factory=list,max_length=6)
    @model_validator(mode='after')
    def check_context(self):
        if self.final_k>self.top_k:raise ValueError('final_k不能大于top_k')
        build_messages(self.question,[],self.history)
        return self

def create_app(settings=None):
    settings=settings or Settings();store=Store(settings.runtime_dir);pipeline=Pipeline(settings,store)
    application=FastAPI();application.state.pipeline=pipeline
    def get(doc_id):
        try: return store.get(doc_id)
        except KeyError: raise HTTPException(404,'文档不存在') from None
    @application.exception_handler(ProviderError)
    async def provider_error(request,error):
        body={'detail':str(error)}
        if hasattr(error,'run_id'):body.update(run_id=error.run_id,stage=error.stage)
        return JSONResponse(status_code=502,content=body)
    @application.get('/api/services/milvus')
    def milvus_health():
        try:return VectorStore(settings).health()
        except Exception:raise HTTPException(503,'Milvus无法连接，请检查Docker服务和MILVUS_URI') from None
    @application.get('/api/health')
    def health(): return public_health(settings,KINDS)
    @application.get('/api/documents')
    def documents(): return store.list()
    @application.post('/api/documents',status_code=201)
    async def upload(file:UploadFile=File(...)):
        name=re.sub(r'[\x00-\x1f\x7f]','',Path((file.filename or '').replace('\\','/')).name).strip()[:180]
        extension=Path(name).suffix.lower();kind=KINDS.get(extension)
        if not kind: raise HTTPException(415,'暂不支持此文件类型，请选择课程支持的文档')
        doc_id=uuid4().hex;folder=settings.runtime_dir/'documents'/doc_id;folder.mkdir(parents=True)
        digest=sha256();size=0
        try:
            with (folder/('source'+extension)).open('wb') as output:
                while chunk:=await file.read(1024*1024):
                    size+=len(chunk)
                    if size>MAX_BYTES: raise HTTPException(413,'单文件不能超过 50 MB')
                    digest.update(chunk);output.write(chunk)
            if size==0: raise HTTPException(400,'文件为空')
            doc={'doc_id':doc_id,'name':name,'extension':extension,'kind':kind,'size':size,'sha256':digest.hexdigest(),
                 'status':'uploaded','block_count':0,'chunk_count':0,'error':None}
            store.put(doc);return doc
        except Exception:
            shutil.rmtree(folder,ignore_errors=True);raise
        finally: await file.close()
    @application.post('/api/documents/{doc_id}/parse',status_code=202)
    def parse(doc_id:str,tasks:BackgroundTasks):
        get(doc_id)
        try: pipeline.reserve(doc_id,operation='parse')
        except ValueError as exc: raise HTTPException(409,str(exc)) from None
        tasks.add_task(pipeline.parse,doc_id)
        return {'doc_id':doc_id,'accepted':True}
    @application.get('/api/documents/{doc_id}/blocks')
    def blocks(doc_id:str):
        doc=get(doc_id)
        if doc['status'] not in {'parsed','indexing','ready'} and not (doc['status']=='failed' and doc.get('stage')=='index'): raise HTTPException(409,'尚未解析完成，请先检查文档状态')
        return json.loads((store.directory(doc_id)/'blocks.json').read_text(encoding='utf-8'))
    @application.get('/api/documents/{doc_id}/chunks')
    def chunks(doc_id:str):
        get(doc_id)
        try:return pipeline.preview_chunks(doc_id)
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
    @application.post('/api/documents/{doc_id}/index',status_code=202)
    def index(doc_id:str,tasks:BackgroundTasks):
        get(doc_id)
        try:pipeline.reserve(doc_id,operation='index')
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
        tasks.add_task(pipeline.index_only,doc_id)
        return {'doc_id':doc_id,'accepted':True}
    @application.post('/api/retrieve')
    def retrieve(body:RetrieveRequest):
        try:return pipeline.retrieve(**body.model_dump())
        except ProviderError:raise
        except ValueError as exc:raise HTTPException(409,str(exc)) from None
        except Exception:raise HTTPException(503,'候选检索失败，请检查模型、Milvus与索引配置；本次未生成答案') from None
    @application.get('/api/documents/{doc_id}/source-inspection')
    def inspection(doc_id:str):
        get(doc_id)  # 仅元数据不存在才404；内部格式错误不得误报文档不存在。
        try: return pipeline.inspect_source(doc_id)
        except ValueError as exc: raise HTTPException(422,str(exc)) from None
        except Exception: raise HTTPException(422,'原文件或解析缓存无法核对，请检查格式和已保存文件') from None
    @application.get('/api/documents/{doc_id}/source')
    def source(doc_id:str):
        doc=get(doc_id)
        return FileResponse(store.directory(doc_id)/('source'+doc['extension']),filename=doc['name'],media_type='application/octet-stream')
    @application.post('/api/ask')
    def ask(body:AskRequest):
        try:return pipeline.ask(**body.model_dump())
        except ProviderError:raise
        except Exception:raise HTTPException(503,'问答服务失败，请检查本次运行记录和模型配置') from None
    @application.post('/api/ask/stream')
    def ask_stream(body:AskRequest):
        async def events():
            iterator=pipeline.answer_events(**body.model_dump());end=object()
            try:
                while True:
                    # 当前同步读取返回后再close，避免迭代器仍在执行。
                    with anyio.CancelScope(shield=True):
                        event=await run_in_threadpool(next,iterator,end)
                    if event is end:break
                    yield 'data: '+json.dumps(event,ensure_ascii=False)+'\n\n'
            finally:iterator.close()
        return StreamingResponse(events(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
    @application.get('/api/traces/{run_id}')
    def trace(run_id:str):
        if not re.fullmatch(r'[a-f0-9]{32}',run_id):raise HTTPException(404,'本次记录不存在')
        path=settings.runtime_dir/'traces'/f'{run_id}.json'
        if not path.is_file():raise HTTPException(404,'本次记录不存在')
        return json.loads(path.read_text(encoding='utf-8'))
    return application

app=create_app()
