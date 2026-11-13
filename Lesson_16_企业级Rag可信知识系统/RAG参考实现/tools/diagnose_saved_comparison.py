"""Offline stage diagnostics on a public, hash-bound development comparison."""
from pathlib import Path
from hashlib import sha256
import argparse,json,sys
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.generation import build_messages,PROMPT_VERSION

def model_body(row):
 t=row['trace'];g=t['generation']
 if t['prompt_version']!=PROMPT_VERSION or t['generation_profile']['mode']!='baseline':raise ValueError('本诊断器只重建冻结baseline生成协议')
 return {'model':t['models']['chat'],'temperature':g['temperature'],'enable_thinking':g['enable_thinking'],
  'max_tokens':g['max_tokens'],'response_format':{'type':'json_object'},'messages':build_messages(t['question'],t['context'],t['history'])}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--comparison',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 raw=a.comparison.read_bytes();m=json.loads((a.comparison.parent/'manifest.json').read_text(encoding='utf-8'))
 if m['files'].get(a.comparison.name)!=sha256(raw).hexdigest():raise ValueError('比较文件指纹不匹配')
 comparison=json.loads(raw);rows=[]
 for r in comparison['cases']:
  b,c=r['before'],r['after'];s=b['scores'];bt,ct=b['trace'],c['trace']
  rows.append({'case_id':r['case_id'],'primary_task':r['primary_task'],'primary_source_format':r['primary_source_format'],
   'same_candidate_ids':[h['chunk_id'] for h in bt['candidates']]==[h['chunk_id'] for h in ct['candidates']],
   'same_context_object':bt['context']==ct['context'],'same_generation_body':model_body(b)==model_body(c),
   'incomplete_candidate_groups':s['evidence_applicable'] and s['retrieval_recall']<1,
   'incomplete_context_groups':s['evidence_applicable'] and s['context_recall']<1,
   'lost_groups_in_selection':s['evidence_applicable'] and s['context_recall']<s['retrieval_recall'],
   'all_context_groups_but_wrong_answer':s['evidence_applicable'] and s['context_recall']==1 and not s['answer_correct'],
   'right_answer_but_failed_rag':s['answer_correct'] and not s['rag_success']})
 if not rows:raise ValueError('比较数据没有题目')
 fields=[k for k,v in rows[0].items() if type(v) is bool]
 result={'schema_version':'saved-comparison-diagnosis/1','source_sha256':sha256(raw).hexdigest(),'n':len(rows),
   'cloud_requests':0,'observations':{f:sum(r[f] for r in rows) for f in fields},'rows':rows,
   'limitations':['Tags overlap; do not add counts.','Input change is not quality gain.','Reconstruction from saved trace, not network capture.','Specified source groups are not all possible legitimate evidence.']}
 a.output.mkdir(parents=True,exist_ok=False)
 (a.output/'diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 for k,v in result['observations'].items():print(k,':',v,'/',len(rows))
 print('离线诊断完成；云调用0；质量未重新评分。')
if __name__=='__main__':main()
