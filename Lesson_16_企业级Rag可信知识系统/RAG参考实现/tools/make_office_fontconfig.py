"""macOS备用字体配置：只引用系统已安装字体，不下载或复制字体。"""
import argparse,sys
from pathlib import Path
from xml.etree import ElementTree as ET

# checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# revision: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def make(output):
    if sys.platform!='darwin':raise ValueError('此辅助脚本仅用于macOS的Fontconfig转换器；Windows先检查系统中文字体与正式LibreOffice')
    output=Path(output).resolve()
    if output.exists():raise ValueError('配置已存在；先核对，不覆盖已有设置')
    directories=[Path('/System/Library/Fonts/Supplemental'),Path('/System/Library/Fonts')]
    if not all(p.is_dir() for p in directories):raise ValueError('系统字体目录不完整，先检查操作系统安装')
    root=ET.Element('fontconfig')
    for p in directories:ET.SubElement(root,'dir').text=str(p)
    ET.SubElement(root,'cachedir').text=str(output.parent/'font-cache')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:f.write('<?xml version="1.0"?>\n'+ET.tostring(root,encoding='unicode')+'\n')
    print('在.env补充这一行（不要覆盖其他配置）：\nLIBREOFFICE_FONTCONFIG="'+str(output)+'"')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('config/fonts-macos.conf'));a=p.parse_args()
    try:make(a.output)
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
