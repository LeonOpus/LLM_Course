"""Validate a published fixed-evidence experiment, or explicitly replay paid calls."""
import argparse,json,sys,time
from pathlib import Path
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor,as_completed
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from rag_app.config import Settings
from rag_app.providers import Bailian,ProviderError
from rag_app.generation import validate_answer
from rag_app.metering import UsageJournal,summarize_events

def digest(p):return sha256(p.read_bytes()).hexdigest()
def dump(p,o):
 with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,required=True)
 parser.add_argument('--output',type=Path)
 parser.add_argument('--execute',action='store_true',help='明确执行付费生成；不重新检索，不自动重试')
 parser.add_argument('--case-id',action='append',help='可重复指定；默认运行包中全部题，保留每题所有组与重复')
 args=parser.parse_args();source=args.source.resolve()
 manifest=json.loads((source/'export-manifest.json').read_text(encoding='utf-8'))
 for rel,h in manifest['files'].items():
  p=(source/rel).resolve()
  if not p.is_relative_to(source) or not p.is_file() or digest(p)!=h:raise ValueError('材料指纹不匹配：'+rel)
 plan=json.loads((source/'plan.json').read_text(encoding='utf-8'))
 rows=[r for r in plan['plans'] if not args.case_id or r['case_id'] in args.case_id]
 if not rows or (args.case_id and set(args.case_id)-{r['case_id'] for r in rows}):raise ValueError('题号不在本实验包内')
 if len(rows)>plan['limit'] or len({r['id'] for r in rows})!=len(rows):raise ValueError('调用计划重复或超出上限')
 for row in rows:
  p=source/(row['id']+'-request.json')
  if digest(p)!=row['request_sha256']:raise ValueError('请求体指纹不一致')
  body=json.loads(p.read_text(encoding='utf-8'))
  if set(body)!={'model','temperature','enable_thinking','max_tokens','response_format','messages'}:raise ValueError('请求字段超出冻结协议')
  if body['model']!='qwen-plus' or body['max_tokens']!=2048 or body['temperature']!=0 or body['enable_thinking'] is not False:raise ValueError('生成配置不符合冻结协议')
 print('核验通过；选定',len({r['case_id'] for r in rows}),'题，共',len(rows),'次生成请求。',flush=True)
 if not args.execute:
  print('仅离线核验，云调用0。--execute才会调用百炼。');return
 if args.output is None:parser.error('--execute要求新的--output目录')
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 settings=Settings(_env_file=ROOT/'.env')
 if not settings.dashscope_api_key.get_secret_value():raise ValueError('缺少DASHSCOPE_API_KEY，请只在本机.env配置')
 dump(out/'replay-plan.json',{'source_manifest_sha256':digest(source/'export-manifest.json'),'ids':[r['id'] for r in rows],'request_limit':len(rows),'automatic_retries':0,'kind':'fixed-evidence-generation-replay'})
 def one(row):
  name=row['id'];journal=UsageJournal(out,{'run_id':name},origin='configured_transport');p=Bailian(settings,usage_journal=journal);start=time.monotonic()
  body=json.loads((source/(name+'-request.json')).read_text(encoding='utf-8'));dump(out/(name+'-request.json'),body)
  result={k:row[k] for k in ['id','case_id','arm','repeat','request_sha256']}
  try:
   raw=p._post(settings.bailian_base_url.rstrip('/')+'/chat/completions',body)
   choice=raw['choices'][0]
   result.update(execution='ok',response=validate_answer(choice['message']['content'],row['context'],raw.get('usage'),choice.get('finish_reason')))
  except ProviderError as e:result.update(execution='error',error=str(e),raw_model_output=e.model_output)
  except (KeyError,IndexError,ValueError,TypeError):result.update(execution='error',error='模型输出未通过结构/引用校验；没有自动重试')
  finally:p.http.close()
  result.update(elapsed_ms=round((time.monotonic()-start)*1000,3),usage_events=journal.events());dump(out/(name+'-result.json'),result)
  print(name,result['execution'],flush=True);return result
 results=[]
 with ThreadPoolExecutor(max_workers=min(4,len(rows))) as pool:
  for future in as_completed([pool.submit(one,row) for row in rows]):results.append(future.result())
 dump(out/'results.json',sorted(results,key=lambda r:r['id']));dump(out/'usage-summary.json',summarize_events([e for r in results for e in r['usage_events']]))
 print('调用完成；质量待复核。历史评分不能套用到这次新答案。')
if __name__=='__main__':main()
