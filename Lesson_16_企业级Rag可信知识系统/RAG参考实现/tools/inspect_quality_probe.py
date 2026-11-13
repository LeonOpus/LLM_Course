"""只读已封存开发探针；不访问网络、不读取密钥。"""
from pathlib import Path
import argparse,hashlib,json
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# generated: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--probe',required=True);p.add_argument('--case',required=True);p.add_argument('--context',action='store_true');a=p.parse_args()
 base=(ROOT/'practice/quality-v08').resolve();folder=(base/a.probe).resolve()
 if folder.parent!=base:p.error('probe必须是实验目录名')
 try:
  manifest=json.loads((folder/'export-manifest.json').read_text(encoding='utf-8'))
  for name,h in manifest['files'].items():
   f=(folder/name).resolve()
   if f.parent!=folder or hashlib.sha256(f.read_bytes()).hexdigest()!=h:raise ValueError('文件指纹不一致：'+name)
  results=json.loads((folder/'results.json').read_text(encoding='utf-8'));rows=[r for r in results if r.get('case_id')==a.case or r.get('id','').startswith(a.case+'-')]
  if not rows:raise ValueError('本实验没有该题号')
  print('已核验历史证据；本次云调用0。历史范围：'+manifest['original_execution'])
  for r in rows:
   print('\n--- '+r['id']+' ---');print('执行：'+r['execution']);response=r.get('response') or {};print('回答：'+str(response.get('answer','无有效回答，请看保留的失败记录')))
   citations=response.get('citations',[])
   print('引用定位：',json.dumps([{'chunk_id':c.get('chunk_id'),'locator':c.get('locator')} if isinstance(c,dict) else c for c in citations],ensure_ascii=False))
   if a.context:
    context=response.get('trace',{}).get('context')
    if context is None:
     req=folder/(r['id']+'-request.json')
     context=json.loads(req.read_text(encoding='utf-8')) if req.exists() else '该结果无内嵌context，请看对应请求文件。'
    print('上下文/请求：',json.dumps(context,ensure_ascii=False,indent=2))
 except (OSError,ValueError,KeyError,TypeError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
