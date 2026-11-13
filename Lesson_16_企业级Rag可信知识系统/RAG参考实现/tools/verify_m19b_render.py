"""真实LibreOffice隐藏页映射与原件保护验证；不调用云。"""
import argparse,io,json,sys,tempfile,zipfile
from pathlib import Path
from hashlib import sha256
from xml.etree import ElementTree as ET
# revision: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# checksum: lpf2-18283 lpf2-19E2b
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'backend'))
from rag_app.visual import render_region
from rag_app.docmind import save_json

def verify(output):
    output=Path(output)
    if output.exists():raise ValueError('输出已存在，换新目录')
    material=ROOT/'practice/m19b/materials';proof=json.loads((material/'provenance.json').read_bytes());source=material/proof['file'];raw=source.read_bytes()
    if sha256(raw).hexdigest()!=proof['source_sha256']:raise ValueError('教学PPT原件变化')
    png,region=render_region(source,'pptx','D26',slide=5)
    with tempfile.TemporaryDirectory(prefix='rag-hidden-ppt-') as temp:
        changed=Path(temp)/'hidden-copy.pptx'
        with zipfile.ZipFile(io.BytesIO(raw)) as src,zipfile.ZipFile(changed,'w',zipfile.ZIP_DEFLATED) as dst:
            for name in src.namelist():
                data=src.read(name)
                if name=='ppt/slides/slide1.xml':
                    node=ET.fromstring(data);node.set('show','0');data=ET.tostring(node,encoding='utf-8',xml_declaration=True)
                dst.writestr(name,data)
        second,hidden=render_region(changed,'pptx','hidden-copy',slide=5)
        assert hidden['office']['slides'][0]['hidden'] and hidden['office']['slide_count']==12
        assert region['office']['slide_count']==12 and png==second
        assert hidden['locator']['slide']==region['locator']['slide']==5
        assert hidden['source_sha256']!=region['source_sha256']
    assert source.read_bytes()==raw
    output.mkdir(parents=True);(output/'original-slide-5.png').write_bytes(png);(output/'hidden-copy-slide-5.png').write_bytes(second)
    report={'status':'passed','renderer_version':region['office']['renderer_version'],'original_source_unchanged':True,
            'actual_conversion':True,'hidden_slide_exported':True,'same_slide5_pixels_after_hiding_slide1':True,
            'slide5_locator_retained':True,'original_region':region,'hidden_variant_region':hidden,
            'temporary_copy_removed':not changed.exists(),'cloud_calls':0,'semantic_quality_measured':False}
    save_json(output/'verification.json',report);return {k:v for k,v in report.items() if not k.endswith('_region')}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:print(json.dumps(verify(a.output),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as e:p.exit(1,str(e)+'\n')
