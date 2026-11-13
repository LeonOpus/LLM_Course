"""导出供应用内质量评估页读取的比较文件，不调用云服务。"""
import argparse,json,sys
from pathlib import Path
# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluation.comparison_view import export_comparison_view

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for key in ['left','right','left-reviews','right-reviews','output']:p.add_argument('--'+key,required=True)
 a=p.parse_args()
 try:
  output=Path(a.output)
  if output.exists():raise ValueError('输出文件已存在，请换新文件名')
  read=lambda f:json.loads(Path(f).read_text(encoding='utf-8'))
  bundle=export_comparison_view(a.left,a.right,read(a.left_reviews),read(a.right_reviews))
  output.parent.mkdir(parents=True,exist_ok=True)
  with output.open('x',encoding='utf-8') as stream:json.dump(bundle,stream,ensure_ascii=False,indent=2,allow_nan=False)
  print('比较文件已生成；在质量评估页导入。待复核题数：'+str(bundle['comparison']['pending']))
 except (ValueError,OSError,KeyError,TypeError) as error:
  p.exit(1,(str(error) if isinstance(error,ValueError) else type(error).__name__+'：检查路径和文件结构')+'\n')

if __name__=='__main__':main()
