"""逐请求标价估算，既不是实际账单，也不推测缺失的计费量。"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from urllib.parse import urlsplit
import json,re
from rag_app.metering import summarize_events

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def digest(value):return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def timestamp(value):
    if not isinstance(value,str):raise ValueError('时间必须为含时区的ISO格式')
    try:d=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise ValueError('时间必须为含时区的ISO格式') from None
    if d.tzinfo is None:raise ValueError('时间必须包含时区')
    return d

def pricing_context(url,body):
    host=urlsplit(url).hostname
    if host is not None and not re.fullmatch(r'[a-z0-9.-]{1,253}',host):host=None
    thinking=body.get('enable_thinking')
    return {'endpoint_host':host,'invocation':'realtime','enable_thinking':thinking if type(thinking) is bool else None}

def money(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+(?:\.\d+)?',value):raise ValueError('价格必须为非负十进制字符串')
    try:d=Decimal(value)
    except InvalidOperation:raise ValueError('价格格式无效') from None
    if not d.is_finite() or not 0<=d<=1000000:raise ValueError('价格超出允许范围')
    return d

def decimal_text(value):return format(value.normalize(),'f')

def valid_card(card):
    if not isinstance(card,dict) or card.get('schema_version')!='rag-price-card/1' or card.get('currency')!='CNY':raise ValueError('价格卡结构或币种不支持')
    if not card.get('source_url','').startswith('https://') or not isinstance(card.get('reviewed_on'),str):raise ValueError('价格卡必须记录来源和核查日期')
    start,end=timestamp(card.get('valid_from')),timestamp(card.get('valid_until'))
    if start>=end:raise ValueError('价格卡适用窗口无效')
    rules=card.get('rules');seen=set()
    if not isinstance(rules,list) or not rules:raise ValueError('价格规则不能为空')
    for rule in rules:
        if not isinstance(rule,dict) or not isinstance(rule.get('id'),str) or rule['id'] in seen:raise ValueError('规则编号必须唯一')
        seen.add(rule['id'])
        if rule.get('operation') not in {'answer','query_rewrite','embedding','rerank','judge','vision'} or not isinstance(rule.get('model'),str):raise ValueError('价格操作或模型无效')
        if rule.get('invocation')!='realtime' or rule.get('enable_thinking') is not None and type(rule['enable_thinking']) is not bool:raise ValueError('调用模式无效')
        hosts=rule.get('hosts')
        if not isinstance(hosts,list) or not hosts or any(not isinstance(h,str) or not re.fullmatch(r'(?:\*\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+',h) for h in hosts):raise ValueError('主机匹配规则无效')
        if rule.get('kind') not in {'input_only','chat'}:raise ValueError('计费种类无效')
        tiers=rule.get('tiers')
        if not isinstance(tiers,list) or not tiers:raise ValueError('档位不能为空')
        previous=0
        for t in tiers:
            if type(t.get('input_max')) is not int or t['input_max']<=previous:raise ValueError('档位上限须严格递增')
            previous=t['input_max'];money(t.get('input_per_million'));money(t.get('output_per_million'))
            if rule['kind']=='input_only' and money(t['output_per_million'])!=0:raise ValueError('只计输入的规则不能有输出价格')
    # 规则交叉不允许依赖顺序；完全或通配主机重叠都拒绝。
    for i,a in enumerate(rules):
        for b in rules[i+1:]:
            if all(a.get(k)==b.get(k) for k in ('operation','model','invocation','enable_thinking')):
                if any(host_match(x,y) or host_match(y,x) for x in a['hosts'] for y in b['hosts']):raise ValueError('价格规则重叠')
    return start,end

def host_match(host,pattern):
    if not isinstance(host,str):return False
    if pattern.startswith('*.'):
        suffix=pattern[1:]
        return host.endswith(suffix) and bool(re.fullmatch('[a-z0-9-]+',host[:-len(suffix)]))
    return host==pattern

def price_one(e,card,start,end):
    def unknown(reason):return {'status':'unknown','reason':reason,'estimated_cny':None}
    if not e['request_attempted']:return {'status':'local_cache','reason':'no_new_cloud_request','estimated_cny':None}
    if e['outcome'] not in {'response_received','stream_completed'}:return unknown('incomplete_or_failed_transport')
    try:when=timestamp(e.get('started_at'))
    except ValueError:return unknown('missing_or_invalid_request_time')
    if not start<=when<end:return unknown('outside_card_window')
    context=e.get('pricing_context')
    if not isinstance(context,dict) or set(context)!={'endpoint_host','invocation','enable_thinking'}:return unknown('missing_pricing_context')
    if type(context.get('enable_thinking')) is not bool and context.get('enable_thinking') is not None:return unknown('invalid_pricing_context')
    candidates=[r for r in card['rules'] if r['operation']==e['operation'] and r['model']==e['model'] and all(r[k]==context[k] for k in ('invocation','enable_thinking')) and any(host_match(context['endpoint_host'],p) for p in r['hosts'])]
    if not candidates:return unknown('no_matching_rule')
    if len(candidates)>1:raise ValueError('事件匹配多个价格规则')
    rule=candidates[0];usage=e['usage'];c=usage['counts']
    if usage.get('issues') or usage.get('present') is not True:return unknown('invalid_or_missing_usage')
    inp,out,total=(c[k] for k in ('input_tokens','output_tokens','total_tokens'))
    if all(x is not None for x in (inp,out,total)) and inp+out!=total:return unknown('inconsistent_usage')
    if c['cached_input_tokens'] is not None and inp is not None and c['cached_input_tokens']>inp:return unknown('inconsistent_usage')
    if rule['kind']=='input_only':
        if total is None:return unknown('missing_total_tokens')
        if out not in (None,0) or inp is not None and inp!=total:return unknown('inconsistent_input_only_usage')
        inp,out=total,0
    if inp is None or out is None:return unknown('missing_input_or_output_tokens')
    if inp<=0:return unknown('nonpositive_input_tokens')
    tier=next((t for t in rule['tiers'] if inp<=t['input_max']),None)
    if tier is None:return unknown('outside_supported_tiers')
    amount=(Decimal(inp)*money(tier['input_per_million'])+Decimal(out)*money(tier['output_per_million']))/Decimal(1000000)
    return {'status':'priced','rule_id':rule['id'],'tier_input_max':tier['input_max'],'input_tokens':inp,'output_tokens':out,
            'input_per_million':tier['input_per_million'],'output_per_million':tier['output_per_million'],
            'estimated_cny':decimal_text(amount)}

def estimate(events,card):
    start,end=valid_card(card);summary=summarize_events(events)
    unique={e['event_id']:e for e in events};rows=[]
    for uid,e in sorted(unique.items()):
        rows.append({'event_id':uid,'event_sha256':digest(e),'operation':e['operation'],'model':e['model'],'origin':e.get('origin','unverified'),**price_one(e,card,start,end)})
    priced=[r for r in rows if r['status']=='priced'];unknown=sum(r['status']=='unknown' for r in rows)
    subtotal=sum((Decimal(r['estimated_cny']) for r in priced),Decimal(0))
    return {'schema_version':'rag-cost-estimate/1','currency':'CNY','basis':'standard_list_price_without_discounts',
            'price_card_sha256':digest(card),'source_url':card['source_url'],'reviewed_on':card['reviewed_on'],
            'request_count':summary['request_count'],'priced_request_count':len(priced),'unknown_request_count':unknown,
            'priced_subtotal_cny':decimal_text(subtotal) if priced else None,
            'estimated_total_cny':decimal_text(subtotal) if priced and not unknown else None,'actual_cost_cny':None,
            'origins':summary['origins'],'rows':rows,
            'limitations':['仅覆盖所提供事件，不代表账号完整用量。','按普通实时标价估算，未扣免费额度、促销或云端缓存优惠；不是实际扣款。',
                          '失败或未完成请求不推测费用；已知小计不可代替全量成本。','不含DocMind、基础设施及未记录的评估模型调用。','价格卡时间窗为课程适用限制，并非官方价格有效期承诺。']}
