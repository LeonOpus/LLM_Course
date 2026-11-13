"""只读前端比较包：从冻结记录重新评分，保留未知值与运行来源。"""
from .reporting import score_run
from .runtime import compare_runs

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
def export_comparison_view(left_path,right_path,left_reviews,right_reviews):
 left,cases,left_records=score_run(left_path,left_reviews)
 right,_,right_records=score_run(right_path,right_reviews)
 comparison=compare_runs(left,right)
 def run(summary):
  manifest=summary['manifest']
  return {**{k:summary[k] for k in ['planned','execution_counts','review_status','metrics','latency_ms','tokens','query_rewrite_tokens','request_usage','cost']},
   'config':manifest['config'],'observed_configurations':manifest.get('observed_configurations',[]),
   'fingerprints':{k:manifest[k] for k in ['cases_sha256','corpus_sha256','records_sha256','config_sha256','scoring_version']}}
 def row(record,score):
  response=record.get('response',{})
  return {'execution':record['execution'],'elapsed_ms':record.get('elapsed_ms'),
   'answer':response.get('answer'),'status':response.get('status'),'citations':response.get('citations',[]),
   'trace':response.get('trace',{}),'scores':score}
 a={r['case_id']:r for r in left_records};b={r['case_id']:r for r in right_records}
 sa={s['case_id']:s for s in left['scores']};sb={s['case_id']:s for s in right['scores']}
 pairs={p['case_id']:p for p in comparison['pairs']}
 return {'schema_version':'rag-comparison-view/1','verification':'recomputed_from_frozen_records',
  'comparison':comparison,'runs':{'before':run(left),'after':run(right)},
  'cases':[{'case_id':c['case_id'],'question':c['question'],'primary_task':c.get('primary_task'),
   'primary_source_format':c.get('primary_source_format'),'change':pairs[c['case_id']]['change'],
   'before':row(a[c['case_id']],sa[c['case_id']]),'after':row(b[c['case_id']],sb[c['case_id']])} for c in cases],
  'limitations':['浏览器导入不重新读取原始运行目录；应使用本工具生成，来源标记不是数字签名。',
   '百分比与差值只针对已复核且适用的配对子集；未复核不等于错误。',
   '固定响应演练不代表模型效果；模型辅助复核仍需人工核查。',
   'Token仅包含响应已返回用量；未知成本不等于免费。']}
