"""百炼真实 HTTP 适配器；固定样例只通过 tests 注入 transport。"""
import json
import math
import httpx
from rag_app.core import apply_rerank
from rag_app.metering import UsageJournal
from rag_app.pricing import pricing_context

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
class ProviderError(RuntimeError):
    """适合显示给学员的脱敏服务错误。"""
    def __init__(self,message,model_output=None):
        super().__init__(message)
        # 只供本机trace复核；不把完整HTTP响应、请求头或凭证附到错误中。
        self.model_output=model_output[:96000] if isinstance(model_output,str) else None

class Bailian:
    def __init__(self,settings,http=None,usage_journal=None):
        self.settings=settings
        self.http=http or httpx.Client(timeout=httpx.Timeout(90,connect=15))
        self.usage_journal=usage_journal if usage_journal is not None else UsageJournal()

    def _post(self,url,body,operation='answer',item_count=None):
        key=self.settings.dashscope_api_key.get_secret_value()
        if not key: raise ProviderError('未配置 DASHSCOPE_API_KEY：在项目根目录 .env 中配置并重启后端')
        event=self.usage_journal.begin(operation,body['model'],item_count,pricing_context=pricing_context(url,body))
        try:
            response=self.http.post(url,json=body,headers={'Authorization':f'Bearer {key}'})
        except httpx.TimeoutException:
            self.usage_journal.update(event,outcome='transport_error')
            raise ProviderError('百炼请求超时：检查网络与地域；本次没有自动重复付费请求') from None
        except httpx.HTTPError:
            self.usage_journal.update(event,outcome='transport_error')
            raise ProviderError('无法连接百炼：检查网络、代理及接口地址') from None
        if not response.is_success:
            try:failed=response.json()
            except ValueError:failed=None
            self.usage_journal.update(event,outcome='http_error',http_status=response.status_code,
                                      usage=failed.get('usage') if isinstance(failed,dict) else None)
            hints={401:'检查 API Key 与地域',403:'检查模型权限',429:'检查配额或限流，稍后重试'}
            raise ProviderError(f'百炼 HTTP {response.status_code}：{hints.get(response.status_code,"检查模型、请求参数和控制台状态")}')
        try: raw=response.json()
        except ValueError:
            self.usage_journal.update(event,outcome='invalid_json',http_status=response.status_code)
            raise ProviderError('百炼返回了非 JSON 数据') from None
        self.usage_journal.update(event,outcome='response_received',http_status=response.status_code,
                                  usage=raw.get('usage') if isinstance(raw,dict) else None)
        return raw

    def embed(self,texts):
        if not texts: return []
        if any(not isinstance(t,str) or not t.strip() for t in texts): raise ValueError('向量输入必须是非空文本')
        vectors=[]
        # 保守的小批次；不依赖不断变化的最大批量限制。
        for start in range(0,len(texts),10):
            batch=texts[start:start+10]
            raw=self._post(self.settings.bailian_base_url.rstrip('/')+'/embeddings',
                           {'model':self.settings.embedding_model,'input':batch,
                            'dimensions':self.settings.embedding_dim,'encoding_format':'float'},operation='embedding',item_count=len(batch))
            try:
                rows=raw['data']; mapped={}
                for row in rows:
                    idx=row['index'];v=row['embedding']
                    if type(idx) is not int or idx in mapped or not 0<=idx<len(batch): raise ValueError()
                    if len(v)!=self.settings.embedding_dim or any(type(n) not in (int,float) or not math.isfinite(n) for n in v): raise ValueError()
                    mapped[idx]=v
                if len(mapped)!=len(batch): raise ValueError()
                vectors.extend(mapped[i] for i in range(len(batch)))
            except (KeyError,TypeError,ValueError):
                raise ProviderError('向量响应数量、顺序索引或维度不符合配置；停止入库') from None
        return vectors

    def rerank(self,query,candidates,top_n):
        if not candidates: return []
        if not self.settings.rerank_url:
            raise ProviderError('未配置 RERANK_URL：从百炼当前工作空间文档复制对应重排地址')
        if type(top_n) is not int or top_n<1: raise ValueError('top_n 必须为正整数')
        raw=self._post(self.settings.rerank_url,{'model':self.settings.rerank_model,
            'input':{'query':query,'documents':[x['text'] for x in candidates]},
            'parameters':{'top_n':min(top_n,len(candidates)),'return_documents':False}},operation='rerank',item_count=len(candidates))
        try: return apply_rerank(candidates,raw['output']['results'])[:top_n]
        except (KeyError,TypeError,ValueError): raise ProviderError('重排响应格式或索引异常；请核对模型与接口是否匹配') from None

    def rewrite_query(self,question,history=None):
        from rag_app.rewriting import messages,validate
        body={'model':self.settings.chat_model,'temperature':0,'enable_thinking':False,'max_tokens':384,
              'response_format':{'type':'json_object'},'messages':messages(question,history)}
        raw=self._post(self.settings.bailian_base_url.rstrip('/')+'/chat/completions',body,operation='query_rewrite')
        try:
            choice=raw['choices'][0]
            result=validate(choice['message']['content'],question,history,choice.get('finish_reason'))
            usage=raw.get('usage',{})
            result['usage']={k:v for k,v in usage.items() if k in {'prompt_tokens','completion_tokens','total_tokens'} and type(v) is int and v>=0} if isinstance(usage,dict) else {}
            return result
        except (KeyError,TypeError,ValueError,IndexError):
            raise ProviderError('查询改写格式、结束状态或词面守卫校验失败；本次停止，没有暗中回退') from None

    def transcribe_image(self,png,prompt_version=None):
        from rag_app.visual import request_body,validate_observations,PROMPT_VERSION
        raw=self._post(self.settings.bailian_base_url.rstrip('/')+'/chat/completions',
                       request_body(png,self.settings.vision_model,prompt_version=prompt_version or PROMPT_VERSION),operation='vision',item_count=1)
        content=None
        try:
            choice=raw['choices'][0];content=choice['message']['content']
            observations=validate_observations(content,choice.get('finish_reason'))
            return {'observations':observations,'raw_output':content,'returned_model':raw.get('model'),
                    'validation':'structure_only_not_semantic','finish_reason':choice['finish_reason']}
        except (KeyError,TypeError,ValueError,IndexError):
            raise ProviderError('视觉模型输出结构或结束状态无效；本次不自动重试',model_output=content) from None

    def _answer_body(self,query,hits,history=None):
        from rag_app.generation import build_messages
        from rag_app.ledger import ledger_messages
        from rag_app.complete_answer import complete_messages
        from rag_app.bounded_answer import bounded_messages
        messages={'baseline':build_messages,'evidence_ledger':ledger_messages,'complete_answer':complete_messages,'bounded_answer':bounded_messages}[self.settings.generation_policy]
        return {'model':self.settings.chat_model,'temperature':0,'enable_thinking':False,
                'max_tokens':2048,'response_format':{'type':'json_object'},
                'messages':messages(query,hits,history)}

    def _validate_generated(self,content,hits,query,usage,finish_reason):
        from rag_app.generation import validate_answer
        from rag_app.ledger import validate_ledger
        from rag_app.bounded_answer import validate_bounded
        if self.settings.generation_policy=='bounded_answer':return validate_bounded(content,hits,usage,finish_reason)
        if self.settings.generation_policy=='evidence_ledger':
            return validate_ledger(content,hits,query,usage,finish_reason)
        return validate_answer(content,hits,usage,finish_reason)

    def _empty_answer(self):
        return {'status':'refused','answer':'当前知识库没有可用证据，请补充资料或具体型号。',
                'citations':[],'usage':{},'validation':{'format':'local_response','citation_membership':'not_applicable','semantic_support':'not_evaluated'}}

    def answer(self,query,hits,history=None):
        from rag_app.generation import validate_answer
        if not hits:return self._empty_answer()
        raw=self._post(self.settings.bailian_base_url.rstrip('/')+'/chat/completions',self._answer_body(query,hits,history))
        content=None
        try:
            choice=raw['choices'][0]
            content=choice['message']['content']
            return self._validate_generated(content,hits,query,raw.get('usage'),choice.get('finish_reason'))
        except (KeyError,TypeError,ValueError,IndexError):
            raise ProviderError('回答格式、结束状态或引用校验失败；未展示为正式答案，请核对本次上下文',model_output=content) from None

    def answer_stream(self,query,hits,history=None):
        from rag_app.generation import read_model_stream,validate_answer
        if not hits:
            yield {'type':'answer','result':self._empty_answer()}
            return
        body=self._answer_body(query,hits,history)
        body.update(stream=True,stream_options={'include_usage':True})
        key=self.settings.dashscope_api_key.get_secret_value()
        if not key:raise ProviderError('未配置 DASHSCOPE_API_KEY：在项目根目录 .env 中配置并重启后端')
        event=self.usage_journal.begin('answer',body['model'],pricing_context=pricing_context(self.settings.bailian_base_url,body))
        outcome='stream_incomplete'
        try:
            with self.http.stream('POST',self.settings.bailian_base_url.rstrip('/')+'/chat/completions',
                                  json=body,headers={'Authorization':f'Bearer {key}'}) as response:
                self.usage_journal.update(event,http_status=response.status_code)
                if not response.is_success:
                    outcome='http_error';self.usage_journal.update(event,http_status=response.status_code)
                    raise ProviderError(f'百炼 HTTP {response.status_code}：检查Key、地域、模型权限或额度')
                for item in read_model_stream(response.iter_lines(),on_usage=lambda usage:self.usage_journal.update(event,usage=usage)):
                    if item['type']=='draft':yield item
                    else:
                        outcome='stream_completed'
                        result=self._validate_generated(item['content'],hits,query,item['usage'],item['finish_reason'])
                        self.usage_journal.update(event,outcome=outcome)
                        yield {'type':'answer','result':result}
        except httpx.TimeoutException:raise ProviderError('百炼流式请求超时；未展示为完成答案，不自动重发付费请求') from None
        except httpx.HTTPError:raise ProviderError('百炼流式连接中断；未展示为完成答案') from None
        except ValueError:raise ProviderError('模型流格式、结束状态或引用校验失败；未展示为正式答案') from None
        finally:self.usage_journal.update(event,outcome=outcome)
