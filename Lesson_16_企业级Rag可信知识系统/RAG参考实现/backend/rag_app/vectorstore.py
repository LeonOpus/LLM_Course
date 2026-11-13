"""本课程独立 Milvus collection；不删除或修改其他项目 collection。"""
import json
import math
from pymilvus import MilvusClient, DataType, Function, FunctionType
from rag_app.hybrid import ANALYZER
from rag_app.providers import ProviderError
from rag_app.source_scope import milvus_filter

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
class VectorStore:
    def __init__(self,settings):
        self.settings=settings
        self.name=settings.milvus_collection
        if not self.name.startswith('rag_course_'):
            raise ValueError('课程 collection 名必须以 rag_course_ 开头，避免混入其他项目')
        self.client=MilvusClient(uri=settings.milvus_uri,token=settings.milvus_token.get_secret_value(),timeout=15)

    def ensure_collection(self):
        if self.client.has_collection(self.name):
            desc=self.client.describe_collection(self.name)
            fields={f['name']:f for f in desc['fields']}
            if not {'chunk_id','doc_id','text','vector','source'}<=fields.keys():
                raise ProviderError('已有 collection 的字段不匹配：使用新的课程 collection 名')
            if int(fields['vector']['params']['dim']) != self.settings.embedding_dim:
                raise ProviderError('Milvus 维度与 EMBEDDING_DIM 不一致：新建 collection 并重新入库')
            if self.settings.milvus_full_text:self.verify_full_text(desc)
            return
        schema=self.client.create_schema(auto_id=False,enable_dynamic_field=False)
        schema.add_field('chunk_id',DataType.VARCHAR,is_primary=True,max_length=64)
        schema.add_field('doc_id',DataType.VARCHAR,max_length=128)
        text_options={'enable_analyzer':True,'analyzer_params':ANALYZER} if self.settings.milvus_full_text else {}
        schema.add_field('text',DataType.VARCHAR,max_length=65535,**text_options)
        schema.add_field('vector',DataType.FLOAT_VECTOR,dim=self.settings.embedding_dim)
        schema.add_field('source',DataType.JSON)
        indices=self.client.prepare_index_params()
        indices.add_index(field_name='vector',index_type='AUTOINDEX',metric_type='COSINE')
        if self.settings.milvus_full_text:
            schema.add_field('sparse',DataType.SPARSE_FLOAT_VECTOR)
            schema.add_function(Function(name='course_bm25',input_field_names=['text'],output_field_names=['sparse'],function_type=FunctionType.BM25))
            indices.add_index(field_name='sparse',index_type='SPARSE_INVERTED_INDEX',metric_type='BM25',params={'inverted_index_algo':'DAAT_MAXSCORE','bm25_k1':1.2,'bm25_b':.75})
        self.client.create_collection(collection_name=self.name,schema=schema,index_params=indices,consistency_level='Strong')

    def upsert(self,chunks,vectors):
        if len(chunks)!=len(vectors): raise ValueError('片段数量与向量数量不一致')
        rows=[]
        for chunk,vector in zip(chunks,vectors):
            if len(vector)!=self.settings.embedding_dim or any(type(v) not in (int,float) or not math.isfinite(v) for v in vector):
                raise ValueError('向量维度或数值无效')
            if len(chunk['text'].encode('utf-8'))>65535: raise ValueError('片段文本超过 Milvus 字节上限')
            rows.append({'chunk_id':chunk['chunk_id'],'doc_id':chunk['doc_id'],'text':chunk['text'],'vector':vector,
                         'source':{k:v for k,v in chunk.items() if k not in {'chunk_id','doc_id','text'}}})
        self.ensure_collection()
        for start in range(0,len(rows),100): self.client.upsert(collection_name=self.name,data=rows[start:start+100])
        return len(rows)

    def search(self,vector,top_k=10,doc_ids=None,locator=None):
        if doc_ids==[]: return []
        if len(vector)!=self.settings.embedding_dim: raise ValueError('查询向量维度不一致')
        if not self.client.has_collection(self.name): return []
        expression=milvus_filter(doc_ids,locator)
        results=self.client.search(collection_name=self.name,data=[vector],limit=top_k,filter=expression,
            output_fields=['doc_id','text','source'],anns_field='vector',search_params={'metric_type':'COSINE','params':{}})
        return [normalize_hit(h) for h in results[0]]

    def verify_full_text(self,desc=None):
        if not self.client.has_collection(self.name):raise ProviderError('全文collection不存在；重新准备独立实验并入库')
        desc=desc or self.client.describe_collection(self.name)
        fields={f['name']:f for f in desc['fields']}
        params=fields.get('text',{}).get('params',{})
        analyzer=params.get('analyzer_params')
        if isinstance(analyzer,str):
            try:analyzer=json.loads(analyzer)
            except ValueError:analyzer=None
        functions=desc.get('functions',[])
        valid_function=any(f.get('name')=='course_bm25' and f.get('input_field_names')==['text']
            and f.get('output_field_names')==['sparse'] and int(f.get('type',-1))==int(FunctionType.BM25) for f in functions)
        if (fields.get('sparse',{}).get('type')!=DataType.SPARSE_FLOAT_VECTOR or fields.get('text',{}).get('type')!=DataType.VARCHAR or params.get('enable_analyzer') not in [True,'true'] or analyzer!=ANALYZER or not valid_function):
            raise ProviderError('已有collection缺少约定的中文BM25全文Schema；使用新独立实验，不静默退回dense')
        idx=self.client.describe_index(self.name,'sparse')
        try:valid_params=(float(idx.get('bm25_k1',-1))==1.2 and float(idx.get('bm25_b',-1))==.75)
        except (TypeError,ValueError):valid_params=False
        if (idx.get('metric_type')!='BM25' or idx.get('index_type')!='SPARSE_INVERTED_INDEX'
            or idx.get('inverted_index_algo')!='DAAT_MAXSCORE' or not valid_params):
            raise ProviderError('全文索引参数与冻结BM25配置不同；准备新实验')

    def search_bm25(self,query,top_k=10,doc_ids=None,locator=None):
        if doc_ids==[]:return []
        if not isinstance(query,str) or not query.strip():raise ValueError('BM25查询不能为空')
        self.verify_full_text()
        expression=milvus_filter(doc_ids,locator)
        results=self.client.search(collection_name=self.name,data=[query],anns_field='sparse',limit=top_k,filter=expression,
            output_fields=['doc_id','text','source'],search_params={'metric_type':'BM25','params':{}})
        return [normalize_hit(h) for h in results[0]]

    def health(self):
        self.client.list_collections()
        return {'reachable':True,'collection_exists':self.client.has_collection(self.name)}


def normalize_hit(hit):
    # 3.x 使用实际主键字段名；转换成 dict 避开 SDK Hit 的自定义索引行为。
    raw=dict(hit)
    primary=raw.get('chunk_id',raw.get('id'))
    if primary is None: raise ProviderError('Milvus 返回结果没有片段主键，检查 SDK 与 Schema')
    entity=raw['entity']
    return {**entity['source'],'chunk_id':str(primary),'doc_id':entity['doc_id'],
            'text':entity['text'],'score':float(raw['distance'])}
