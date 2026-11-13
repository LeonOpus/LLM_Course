import json
from hashlib import sha256
from rag_app.source_inspection import inspect_source,reconcile_blocks
from rag_app.core import validate_locator
from threading import Lock
from rag_app.storage import Store
from rag_app.docmind import DocMind
from rag_app.providers import ProviderError
from rag_app.parsing import read_csv_blocks,normalize_layouts

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class Pipeline:
    def __init__(self,settings,store=None):
        self.settings=settings;self.store=store or Store(settings.runtime_dir);self.lock=Lock();self.busy=set()
    def folder(self,doc_id):
        return self.store.directory(doc_id)

    def reserve(self,doc_id,operation='parse'):
        with self.lock:
            doc=self.store.get(doc_id)
            if doc_id in self.busy:raise ValueError('该文档正在处理')
            if operation=='parse':
                if doc['status'] not in {'uploaded','failed','parsing'} or (doc['status']=='failed' and doc.get('stage')=='index'):
                    raise ValueError('文档已有解析结果，请查看内容或继续入库')
            elif operation=='index':
                if doc['status'] not in {'parsed','indexing'} and not (doc['status']=='failed' and doc.get('stage')=='index'):
                    raise ValueError('先完成解析；已入库文档不可重复提交')
            else:raise ValueError('不支持的处理操作')
            self.busy.add(doc_id)
            if operation=='parse':
                try:
                    doc.update(status='parsing',stage='parse',error=None);self.store.put(doc)
                except Exception:
                    self.busy.discard(doc_id);raise
    def parse(self,doc_id):
        doc=self.store.get(doc_id);folder=self.store.directory(doc_id)
        try:
            source=folder/('source'+doc['extension'])
            if doc['kind']=='csv': blocks=read_csv_blocks(doc_id,source)
            else:
                layouts=DocMind(self.settings).parse(source,folder/'docmind',enhance=False)
                blocks=normalize_layouts(doc_id,doc['kind'],layouts,page_base=0)
            if not blocks: raise ValueError('解析结果为空，请核对文档内容')
            temp=folder/'blocks.json.tmp';temp.write_text(json.dumps(blocks,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(folder/'blocks.json')
            doc.update(status='parsed',stage='parse',block_count=len(blocks),chunk_count=0,error=None)
        except (ProviderError,ValueError,UnicodeError) as exc:
            doc.update(status='failed',block_count=0,chunk_count=0,error=str(exc))
        except Exception:
            doc.update(status='failed',block_count=0,chunk_count=0,error='解析发生内部错误，请检查本地服务和文档格式；请勿盲目重复提交云任务')
        finally:
            try: self.store.put(doc)
            finally:
                with self.lock: self.busy.discard(doc_id)

    def inspect_source(self,doc_id):
        doc=self.store.get(doc_id);folder=self.folder(doc_id)
        source=folder/('source'+doc['extension'])
        if sha256(source.read_bytes()).hexdigest()!=doc['sha256']:
            raise ValueError('原件指纹与上传记录不一致，请另存版本并重新上传')
        report=inspect_source(doc_id,source)
        if report['source_sha256']!=doc['sha256']:
            raise ValueError('原件指纹在核对过程中改变，请检查文件版本')
        cached=folder/'blocks.json'
        parsed=json.loads(cached.read_text(encoding='utf-8')) if cached.exists() else []
        if not isinstance(parsed,list):raise ValueError('解析缓存必须是块列表')
        for block in parsed:
            if not isinstance(block,dict) or not isinstance(block.get('text'),str):
                raise ValueError('解析缓存的文本块结构损坏')
            validate_locator(block.get('locator'))
        report['alignment']=reconcile_blocks(parsed,report)
        report['alignment_notice']='仅折叠空白后的整块相等匹配；唯一相等仍只是候选位置，不是质量分数，不改解析块。'
        temporary=folder/'source-inspection.json.tmp'
        temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(folder/'source-inspection.json')
        return report

    def index_only(self,doc_id):
        from rag_app.indexing import index_document
        try:index_document(self,doc_id)
        except Exception as exc:
            doc=self.store.get(doc_id)
            message=str(exc) if isinstance(exc,(ProviderError,ValueError)) else '入库失败，请检查Milvus和配置；保留现有缓存后重试'
            doc.update(status='failed',stage='index',error=message);self.store.put(doc)
        finally:
            with self.lock:self.busy.discard(doc_id)
    def preview_chunks(self,doc_id):
        from rag_app.indexing import preview_chunks
        return preview_chunks(self,doc_id)
    def retrieve(self,question,top_k=10,doc_ids=None):
        from rag_app.indexing import retrieve
        return retrieve(self,question,top_k,doc_ids)

    def answer_events(self,question,strategy='baseline',top_k=10,final_k=5,doc_ids=None,history=None):
        from rag_app.answering import answer_events
        return answer_events(self,question,strategy,top_k,final_k,doc_ids,history,stream=True)

    def ask(self,question,strategy='baseline',top_k=10,final_k=5,doc_ids=None,history=None):
        from rag_app.answering import answer_events,AnswerRunError
        for event in answer_events(self,question,strategy,top_k,final_k,doc_ids,history,stream=False):
            if event['type']=='result':return event['payload']
            if event['type']=='error':raise AnswerRunError(event['message'],event['run_id'],event['stage'])
        raise RuntimeError('问答未产生终态事件')
