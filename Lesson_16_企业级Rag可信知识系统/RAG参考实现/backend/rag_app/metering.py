"""调用计量；只保存白名单元数据。不是账单，也不根据字数估算token。"""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
import json,re,time,math

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
FIELDS=('input_tokens','output_tokens','total_tokens','cached_input_tokens')
OPERATIONS={'embedding','rerank','query_rewrite','answer','judge','vision','embedding_cache'}
OUTCOMES={'request_started','response_received','http_error','transport_error','invalid_json','stream_incomplete','stream_completed','cache_hit'}

def normalize_usage(raw):
    counts={k:None for k in FIELDS};issues=[]
    if not isinstance(raw,dict):return {'counts':counts,'issues':[],'present':False}
    def take(names):
        vals=[];invalid=False
        for name in names:
            if name in raw:
                value=raw[name]
                if type(value) is not int or not 0<=value<=10**15:issues.append('invalid_'+name);invalid=True
                else:vals.append(value)
        if len(set(vals))>1:issues.append('conflicting_'+names[0]);return None
        if invalid:return None
        return vals[0] if vals else None
    counts['input_tokens']=take(['prompt_tokens','input_tokens'])
    counts['output_tokens']=take(['completion_tokens','output_tokens'])
    counts['total_tokens']=take(['total_tokens'])
    cached=[]
    for key in ['prompt_tokens_details','input_tokens_details']:
        detail=raw.get(key)
        if isinstance(detail,dict) and 'cached_tokens' in detail:
            v=detail['cached_tokens']
            if type(v) is int and 0<=v<=10**15:cached.append(v)
            else:issues.append('invalid_cached_tokens')
    if len(set(cached))>1:issues.append('conflicting_cached_tokens')
    elif cached:counts['cached_input_tokens']=cached[0]
    a,b,t=(counts[k] for k in FIELDS[:3])
    if a is not None and b is not None and t is not None and a+b!=t:
        issues.append('inconsistent_total');counts={k:None for k in FIELDS}
    if counts['cached_input_tokens'] is not None and counts['input_tokens'] is not None and counts['cached_input_tokens']>counts['input_tokens']:
        issues.append('cached_exceeds_input');counts['cached_input_tokens']=None
    return {'counts':counts,'issues':issues,'present':True}


class UsageJournal:
    def __init__(self,runtime=None,context=None,origin='unverified'):
        self.folder=Path(runtime)/'usage-events' if runtime is not None else None
        context=context or {}
        if set(context)-{'phase','doc_id','attempt_id','retrieval_id','run_id'}:raise ValueError('用量上下文字段不支持')
        if any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',v) for v in context.values()):raise ValueError('用量上下文只接受短标识符')
        if origin not in {'unverified','configured_transport','fixture'}:raise ValueError('用量来源标记无效')
        self.context=deepcopy(context);self.origin=origin;self._events={};self._started={}

    def _write(self,event):
        if self.folder is None:return
        self.folder.mkdir(parents=True,exist_ok=True)
        path=self.folder/(event['event_id']+'.json');temporary=path.with_suffix('.'+uuid4().hex+'.tmp')
        try:
            temporary.write_text(json.dumps(event,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
            temporary.replace(path)
        finally:temporary.unlink(missing_ok=True)

    def begin(self,operation,model,item_count=None,pricing_context=None):
        if operation not in OPERATIONS or not isinstance(model,str) or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,128}',model):raise ValueError('操作或模型标识无效')
        if item_count is not None and (type(item_count) is not int or item_count<0):raise ValueError('输入项数无效')
        uid=uuid4().hex
        event={'schema_version':'rag-usage-event/1','event_id':uid,'service':'bailian','operation':operation,'model':model,
               'origin':self.origin,'context':deepcopy(self.context),'started_at':datetime.now(timezone.utc).isoformat(),
               'outcome':'request_started','request_attempted':True,'item_count':item_count,'elapsed_ms':None,
               'usage':normalize_usage(None),'cost':None}
        if pricing_context is not None:
            if not isinstance(pricing_context,dict) or set(pricing_context)!={'endpoint_host','invocation','enable_thinking'}:raise ValueError('价格上下文字段无效')
            event['pricing_context']=deepcopy(pricing_context)
        if operation=='embedding_cache':
            if item_count is None or item_count<1:raise ValueError('缓存命中须为正整数')
            event.update(service='local',request_attempted=False,outcome='cache_hit',cache_hits=item_count,elapsed_ms=0.)
        self._events[uid]=event;self._started[uid]=time.perf_counter();self._write(event);return uid

    def update(self,uid,*,outcome=None,usage=None,http_status=None):
        event=self._events[uid]
        if outcome is not None:
            if outcome not in OUTCOMES:raise ValueError('调用状态无效')
            event['outcome']=outcome
        if usage is not None:event['usage']=normalize_usage(usage)
        if http_status is not None:
            if type(http_status) is not int or not 100<=http_status<=599:raise ValueError('HTTP状态无效')
            event['http_status']=http_status
        event['elapsed_ms']=round((time.perf_counter()-self._started[uid])*1000,3)
        self._write(event)

    def record_cache(self,model,hit_count):
        if type(hit_count) is not int or hit_count<1:raise ValueError('缓存命中须为正整数')
        return self.begin('embedding_cache',model,hit_count)

    def events(self):return deepcopy(list(self._events.values()))


def summarize_events(events):
    unique={}
    for e in events:
        if not isinstance(e,dict) or e.get('schema_version')!='rag-usage-event/1':raise ValueError('用量事件结构无效')
        uid=e.get('event_id')
        if not isinstance(uid,str) or not re.fullmatch('[0-9a-f]{32}',uid):raise ValueError('用量事件编号无效')
        if uid in unique and unique[uid]!=e:raise ValueError('同一用量事件有冲突版本，不能静默去重')
        if e.get('operation') not in OPERATIONS or e.get('outcome') not in OUTCOMES:raise ValueError('用量操作或状态无效')
        if type(e.get('request_attempted')) is not bool:raise ValueError('调用标记无效')
        usage=e.get('usage')
        if not isinstance(usage,dict) or not isinstance(usage.get('counts'),dict):raise ValueError('用量计数结构无效')
        counts=usage['counts']
        if set(counts)!=set(FIELDS) or any(v is not None and (type(v) is not int or not 0<=v<=10**15) for v in counts.values()):raise ValueError('用量计数无效')
        elapsed=e.get('elapsed_ms')
        if elapsed is not None and (type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0):raise ValueError('调用耗时无效')
        if not isinstance(e.get('model'),str) or not e['model']:raise ValueError('用量模型标识无效')
        if e['operation']=='embedding_cache':
            if e['request_attempted'] or e['outcome']!='cache_hit' or type(e.get('cache_hits')) is not int or e['cache_hits']<1:raise ValueError('缓存事件不应为云调用')
        elif not e['request_attempted']:raise ValueError('云请求缺少尝试标记')
        unique[uid]=e
    rows=list(unique.values());operations={}
    for op in sorted({e['operation'] for e in rows}):
        group=[e for e in rows if e['operation']==op and e['request_attempted']]
        if not group:continue
        tokens={}
        for field in FIELDS:
            known=[e['usage']['counts'][field] for e in group if e['usage']['counts'][field] is not None]
            tokens[field]={'known_total':sum(known) if known else None,'known_n':len(known),'unknown_n':len(group)-len(known)}
        operations[op]={'requests':len(group),'models':sorted({e['model'] for e in group}),
                        'outcomes':dict(Counter(e['outcome'] for e in group)),'tokens':tokens,
                        'elapsed_ms_known_sum':sum(e['elapsed_ms'] for e in group if type(e.get('elapsed_ms')) in (int,float)),
                        'elapsed_unknown_n':sum(e.get('elapsed_ms') is None for e in group)}
    return {'schema_version':'rag-usage-summary/1','event_count':len(rows),'request_count':sum(e['request_attempted'] for e in rows),
            'cache_hits':sum(e.get('cache_hits',0) for e in rows),'operations':operations,
            'origins':dict(Counter(e.get('origin','unverified') for e in rows)),
            'event_ids':sorted(unique),'cost':None,
            'limitations':['只统计所提供事件；旧版本未记录的请求无法推断为0。','输入、输出和总token各自汇总，不能三列相加。',
                           '请求失败、取消或没有usage不代表免费；金额仍需价格卡和账单核对。','不包含DocMind计费页、未接入的评估模型与基础设施费用。']}
