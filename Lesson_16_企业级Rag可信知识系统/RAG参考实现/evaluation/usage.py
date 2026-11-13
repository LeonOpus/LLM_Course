"""从已冻结回答事件重新计量；失败HTTP或旧记录缺事件时保持缺口。"""
from backend.rag_app.metering import summarize_events

# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
def summarize_record_usage(records):
    events=[];missing=0;present=0
    for record in records:
        trace=record.get('response',{}).get('trace',{})
        value=trace.get('usage_events')
        if value is None:missing+=1;continue
        if not isinstance(value,list):raise ValueError('回答用量事件必须为列表')
        present+=1;events.extend(value)
    result=summarize_events(events)
    return {**result,'records_with_events':present,'records_without_events':missing,
            'scope':'仅本批响应内保存的在线请求事件；不含入库或未返回trace的失败请求',
            'duplicate_references':len(events)-result['event_count'],
            'coverage_notice':'缺事件及失败请求需结合runtime/usage-events核查；recorded不证明云真实性，未知不补0。'}
