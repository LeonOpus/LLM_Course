from rag_app.rewriting import profile as rewrite_profile, skip_reason, fuse_query_results
from rag_app.providers import Bailian,ProviderError
from rag_app.generation import select_context,build_messages,PROMPT_VERSION
from rag_app.ledger import generation_profile
from rag_app.docmind import save_json
from uuid import uuid4
import time
from rag_app.metering import UsageJournal,summarize_events
from rag_app.context import context_profile,select_for_pipeline

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
class AnswerRunError(ProviderError):
    def __init__(self,message,run_id,stage):
        super().__init__(message);self.run_id=run_id;self.stage=stage

def answer_events(pipeline,question,strategy='baseline',top_k=10,final_k=5,doc_ids=None,history=None,stream=True):
    build_messages(question,[],history)
    if strategy not in {'baseline','rerank'}:raise ValueError('不支持的策略')
    if type(top_k) is not int or not 1<=top_k<=50 or type(final_k) is not int or not 1<=final_k<=min(top_k,20):raise ValueError('top_k或final_k无效')
    started=time.perf_counter();run_id=uuid4().hex;settings=pipeline.settings
    journal=UsageJournal(settings.runtime_dir,{'phase':'answer','run_id':run_id},origin='configured_transport')
    provider=Bailian(settings,usage_journal=journal)
    path=settings.runtime_dir/'traces'/f'{run_id}.json'
    trace={'run_id':run_id,'status':'running','stage':'retrieve','question':question.strip(),'history':history or [],
           'strategy':strategy,'top_k':top_k,'final_k':final_k,'context_max_chars':settings.context_max_chars,'prompt_version':PROMPT_VERSION,
           'models':{'embedding':settings.embedding_model,'chat':settings.chat_model,'rerank':settings.rerank_model if strategy=='rerank' else None},
           'generation':{'temperature':0,'max_tokens':2048,'enable_thinking':False,'stream':stream},
           'candidates':[],'context':[],'timing':{},'raw_model_output':'','raw_model_output_status':'unvalidated'}
    trace['query_rewrite_profile']=rewrite_profile(settings,top_k)
    trace['generation_profile']=generation_profile(settings)
    trace['context_profile']=context_profile(settings.context_policy,max_chars=settings.context_max_chars)
    trace['prompt_version']=trace['generation_profile']['prompt_version']
    trace['query_rewrite']={'decision':'not_attempted','attempted':False,'usage':{}}
    trace['query_retrievals']={}
    retrieval_events=[]
    def sync_usage():
        trace['usage_events']=retrieval_events+journal.events()
        trace['usage_summary']=summarize_events(trace['usage_events'])
    sync_usage()
    upstream=None
    try:
        save_json(path,trace)
        yield {'type':'phase','run_id':run_id,'stage':'retrieve'}
        retrieval=pipeline.retrieve(question.strip(),top_k=top_k,doc_ids=doc_ids)
        retrieval_events.extend(retrieval.get('usage_events',[]))
        trace.update(mode=retrieval['mode'],candidates=retrieval['candidates'],embedding=retrieval.get('embedding'))
        trace['index_profile']=retrieval.get('index_profile')
        trace['retrieval_profile']=retrieval.get('retrieval_profile')
        trace['retrieval_routes']=retrieval.get('retrieval_routes')
        trace['source_scope']=retrieval.get('source_scope')
        trace['source_scope_profile']={'mode':settings.source_scope,'version':'explicit-registered-document-page-v1'}
        trace['query_retrievals']['original']=retrieval
        trace['timing'].update(retrieval['timing']);trace['timing']['query_rewrite_ms']=0
        reason=skip_reason(settings.query_rewrite,question,history,retrieval['mode'])
        if reason is not None:
            trace['query_rewrite']['decision']=reason
        else:
            trace['stage']='query_rewrite';trace['query_rewrite']['attempted']=True;save_json(path,trace)
            yield {'type':'phase','run_id':run_id,'stage':'query_rewrite'}
            t=time.perf_counter()
            try:rewritten=provider.rewrite_query(question.strip(),history)
            finally:trace['timing']['query_rewrite_ms']=(time.perf_counter()-t)*1000
            trace['query_rewrite'].update(rewritten)
            if rewritten['action']=='keep':trace['query_rewrite']['decision']='kept_by_model'
            elif rewritten['query']==question.strip():trace['query_rewrite']['decision']='unchanged'
            else:
                trace['query_rewrite']['decision']='rewritten';trace['stage']='retrieve_rewritten';save_json(path,trace)
                yield {'type':'phase','run_id':run_id,'stage':'retrieve_rewritten'}
                second=pipeline.retrieve(rewritten['query'],top_k=top_k,doc_ids=doc_ids)
                retrieval_events.extend(second.get('usage_events',[]))
                trace['query_retrievals']['rewritten']=second
                for field in ['index_profile','retrieval_profile','ready_doc_ids','embedding']:
                    if retrieval.get(field) is None or retrieval.get(field)!=second.get(field):
                        raise ValueError('原问题与改写的索引、配置或文档范围不一致，不能合并')
                t=time.perf_counter();trace['candidates']=fuse_query_results(retrieval['candidates'],second['candidates'],top_k)
                trace['timing']['query_fusion_ms']=(time.perf_counter()-t)*1000
                for key,value in second['timing'].items():
                    if key!='total_ms':trace['timing'][key]=trace['timing'].get(key,0)+value
        trace['stage']='context'
        t=time.perf_counter()
        if strategy=='rerank' and trace['candidates']:
            trace['stage']='rerank';save_json(path,trace)
        ordered=provider.rerank(question,trace['candidates'],final_k) if strategy=='rerank' and trace['candidates'] else trace['candidates']
        trace['reranked']=ordered if strategy=='rerank' else None
        trace['timing']['rerank_ms']=(time.perf_counter()-t)*1000 if strategy=='rerank' else 0
        trace['stage']='context'
        t=time.perf_counter()
        selection=select_for_pipeline(pipeline,ordered,trace.get('index_profile'),final_k=final_k,max_chars=settings.context_max_chars)
        trace['timing']['context_ms']=(time.perf_counter()-t)*1000
        trace['selection']={k:v for k,v in selection.items() if k!='hits'};trace['context']=selection['hits']
        save_json(path,trace)
        yield {'type':'context','run_id':run_id,'candidates':trace['candidates'],'reranked':trace['reranked'],'context':trace['context'],'selection':trace['selection']}
        trace['stage']='generate';t=time.perf_counter();save_json(path,trace)
        yield {'type':'phase','run_id':run_id,'stage':'generate'}
        result=None
        if stream:
            upstream=provider.answer_stream(question.strip(),trace['context'],history=history)
            for event in upstream:
                if event['type']=='draft':
                    trace['raw_model_output']+=event['text']
                    yield {'type':'draft','run_id':run_id,'text':event['text'],'verified':False}
                elif event['type']=='answer':result=event['result']
        else:result=provider.answer(question.strip(),trace['context'],history=history)
        if result is None:raise ProviderError('生成流结束但没有通过校验的结果')
        trace['timing']['generate_ms']=(time.perf_counter()-t)*1000
        trace['timing']['total_ms']=(time.perf_counter()-started)*1000
        sync_usage()
        trace.update(status='completed',stage='completed',result=result,raw_model_output_status='format_and_membership_checked' if trace['raw_model_output'] else 'not_captured')
        save_json(path,trace)
        yield {'type':'result','payload':{**result,'run_id':run_id,'timing':trace['timing'],'trace':trace}}
    except Exception as error:
        retrieval_events.extend(getattr(error,'usage_events',[]))
        sync_usage()
        if isinstance(error,ProviderError) and error.model_output is not None:
            trace['raw_model_output']=error.model_output
            trace['raw_model_output_status']='unvalidated'
        message=str(error) if isinstance(error,(ValueError,ProviderError)) else f'问答在{trace["stage"]}阶段失败（{type(error).__name__}），请核对服务与本次记录'
        if trace['stage']=='query_rewrite':trace['query_rewrite']['decision']='failed'
        trace.update(status='failed',error=message)
        trace['timing']['total_ms']=(time.perf_counter()-started)*1000
        save_json(path,trace)
        yield {'type':'error','run_id':run_id,'stage':trace['stage'],'message':message}
    finally:
        if upstream is not None and hasattr(upstream,'close'):upstream.close()
        sync_usage()
        if trace['status']=='running':
            trace.update(status='cancelled',cancel_notice='已关闭本次消费；上游停止及计费时点不能据此保证')
            trace['timing']['total_ms']=(time.perf_counter()-started)*1000
            save_json(path,trace)
