"""查看本地辅助评分进度；不请求模型，不修改记录。"""
from pathlib import Path
from collections import Counter
import argparse,json,re
# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',required=True);a=p.parse_args();folder=Path(a.folder)
try:
 batch=json.loads((folder/'batch.json').read_text(encoding='utf-8'));rows=[];writing=[]
 for f in sorted(folder.glob('Q*.json')):
  if not re.fullmatch(r'Q\d{3}\.json',f.name):continue
  try:rows.append(json.loads(f.read_text(encoding='utf-8')))
  except ValueError:writing.append(f.name)
 print(json.dumps({'batch_status':batch['status'],'planned':len(batch['selected_case_ids']),'saved_case_results':len(rows),'statuses':dict(Counter(r['status'] for r in rows)),'currently_writing_files':writing,'cloud_calls_this_command':0,'notice':'保存结果数量是执行进度，accepted_provisional仍是模型暂评；不是正确题数。'},ensure_ascii=False,indent=2))
except (OSError,ValueError,KeyError,TypeError) as e:p.exit(1,type(e).__name__+'：检查评分目录是否正确、批次是否已经开始。不要重复启动同一评分。\n')
