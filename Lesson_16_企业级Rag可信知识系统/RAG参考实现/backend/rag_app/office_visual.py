"""Render an original PPTX in slide order using an isolated LibreOffice profile."""
import io,json,os,re,shutil,subprocess,tempfile,zipfile
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
from rag_app.config import Settings

# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# revision: lpf2-18283 lpf2-19E2b
P='http://schemas.openxmlformats.org/presentationml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
FILTER={'ExportHiddenSlides':{'type':'boolean','value':'true'},
        'ExportNotesPages':{'type':'boolean','value':'false'},'ExportOnlyNotesPages':{'type':'boolean','value':'false'}}

def ppt_manifest(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or sum(i.file_size for i in z.infolist())>160*1024*1024:raise ValueError('PPTX重复条目或解压大小超过课程上限')
            document=ET.fromstring(z.read('ppt/presentation.xml'))
            rels=ET.fromstring(z.read('ppt/_rels/presentation.xml.rels'))
            relationships={r.get('Id'):r for r in rels}
            if len(relationships)!=len(rels):raise ValueError('PPTX关系编号重复')
            size=document.find('{'+P+'}sldSz');dimensions=[int(size.get('cx')),int(size.get('cy'))]
            if any(x<=0 for x in dimensions):raise ValueError('幻灯片尺寸无效')
            slides=[];seen=set();ids=set()
            for i,s in enumerate(document.findall('./{'+P+'}sldIdLst/{'+P+'}sldId')):
                if not s.get('id','').isdigit() or not 256<=int(s.get('id'))<2**31:raise ValueError('幻灯片slide_id无效')
                rel=relationships[s.get('{'+R+'}id')];target=rel.get('Target','')
                if rel.get('Type')!=R+'/slide' or rel.get('TargetMode')=='External':raise ValueError('幻灯片关系不是内部slide')
                part=target.lstrip('/') if target.startswith('/ppt/') else 'ppt/'+target
                if not re.fullmatch(r'ppt/slides/[^/]+\.xml',part) or part in seen or s.get('id') in ids:raise ValueError('幻灯片目标或编号异常')
                slide=ET.fromstring(z.read(part));show=slide.get('show','1')
                if show not in {'0','1','true','false'}:raise ValueError('隐藏页属性异常')
                seen.add(part);ids.add(s.get('id'))
                slides.append({'slide':i+1,'slide_id':s.get('id'),'slide_part':part,'hidden':show in {'0','false'}})
            if not 1<=len(slides)<=200:raise ValueError('本节接受1至200张幻灯片')
            return {'slide_count':len(slides),'slide_size_emu':dimensions,'slides':slides}
    except (zipfile.BadZipFile,KeyError,ET.ParseError,AttributeError,TypeError):raise ValueError('PPTX结构不完整；不能推测幻灯片顺序') from None

def resolve_binary(explicit=None):
    configured=Settings().libreoffice_bin if explicit is None else explicit
    if configured:
        p=Path(configured).expanduser()
        if not p.is_file():raise ValueError('LIBREOFFICE_BIN未指向可执行文件，不能填写安装目录或附加参数')
        return str(p.resolve())
    for name in ['soffice.com','soffice','libreoffice']:
        found=shutil.which(name)
        if found:return found
    for p in [Path('/Applications/LibreOffice.app/Contents/MacOS/soffice'),Path(os.environ.get('ProgramFiles','C:/Program Files'))/'LibreOffice/program/soffice.com']:
        if p.is_file():return str(p)
    raise ValueError('找不到LibreOffice；按5.19B安装并配置LIBREOFFICE_BIN。PDF和图片功能无需此软件')

def cjk_integrity(expected,text):
    found=set(re.findall(r'[\u4e00-\u9fff]',text));matched=len(expected&found)
    coverage=matched/len(expected) if expected else None
    if coverage is not None and coverage<.8:raise ValueError('渲染中文文本严重缺失或错码；检查中文字体和LIBREOFFICE_FONTCONFIG，不能继续识图')
    return {'expected_unique_cjk':len(expected),'matched_unique_cjk':matched,'unique_cjk_coverage':coverage,
            'threshold':.8,'scope':'native_text_corruption_guard_not_visual_or_semantic_certification'}

def convert_ppt(raw,binary=None):
    manifest=ppt_manifest(raw);binary=resolve_binary(binary)
    env=os.environ.copy();fontconfig=Settings().libreoffice_fontconfig or env.get('FONTCONFIG_FILE','')
    font_identity={'mode':'system_default'}
    if fontconfig:
        path=Path(fontconfig).expanduser()
        if not path.is_file():raise ValueError('字体配置文件不存在，检查LIBREOFFICE_FONTCONFIG')
        env['FONTCONFIG_FILE']=str(path.resolve());font_identity={'mode':'explicit_fontconfig','sha256':sha256(path.read_bytes()).hexdigest()}
    try:
        version=subprocess.run([binary,'--version'],text=True,capture_output=True,timeout=10,env=env)
        if version.returncode or not version.stdout.strip().startswith('LibreOffice'):raise ValueError('不能读取LibreOffice版本；检查可执行文件')
        with tempfile.TemporaryDirectory(prefix='rag-ppt-render-') as tmp:
            folder=Path(tmp);source=folder/'source.pptx';source.write_bytes(raw);out=folder/'out';out.mkdir()
            command=[binary,'-env:UserInstallation='+(folder/'profile').as_uri(),'--headless','--convert-to',
                     'pdf:impress_pdf_Export:'+json.dumps(FILTER,separators=(',',':')),'--outdir',str(out),str(source)]
            result=subprocess.run(command,text=True,capture_output=True,timeout=60,env=env)
            converted=out/'source.pdf'
            if result.returncode or not converted.is_file():raise ValueError('LibreOffice转换失败或未输出PDF；保留原件，检查软件及字体')
            pdf=converted.read_bytes()
            if not pdf.startswith(b'%PDF-') or len(pdf)>80*1024*1024:raise ValueError('转换输出不是受限PDF')
    except subprocess.TimeoutExpired:raise ValueError('LibreOffice转换或版本检查超时；本次不调用视觉模型') from None
    except OSError:raise ValueError('无法启动LibreOffice；检查路径与执行权限') from None
    import pypdfium2 as pdfium
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        native=[set(re.findall(r'[\u4e00-\u9fff]',''.join(t.text or '' for t in ET.fromstring(z.read(s['slide_part'])).iter('{http://schemas.openxmlformats.org/drawingml/2006/main}t')))) for s in manifest['slides']]
    checks=[]
    document=pdfium.PdfDocument(pdf)
    try:
        if len(document)!=manifest['slide_count']:raise ValueError('转换页数与原幻灯片数不一致，不能绑定来源')
        expected=manifest['slide_size_emu'][0]/manifest['slide_size_emu'][1]
        for i in range(len(document)):
            page=document[i]
            try:
                w,h=page.get_size();text_page=page.get_textpage()
                try:checks.append(cjk_integrity(native[i],text_page.get_text_range()))
                finally:text_page.close()
            finally:page.close()
            if h<=0 or abs(w/h-expected)/expected>.005:raise ValueError('转换页面比例异常，可能导出了备注或讲义')
    finally:document.close()
    return pdf,{**manifest,'renderer':'libreoffice-impress-pdf','renderer_version':version.stdout.strip(),
                'font_configuration':font_identity,'native_text_checks':checks,
                'export_options':FILTER,'mapping':'all_slides_in_presentation_order_including_hidden'}
