#!/usr/bin/env python3
"""Build a static GitHub Pages edition without altering the local study documents."""
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from html import escape, unescape
import re, shutil, subprocess

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / '技术总结文档'
OUT = ROOT / '_pages_build'
BASE = 'https://github.com/LeonOpus/LLM_Course'
files = subprocess.check_output(['git', 'ls-files', '-z', '--', '技术总结文档/*.html'], cwd=ROOT).split(b'\0')
docs = sorted((ROOT / p.decode() for p in files if p), key=lambda p: (0 if p.name.startswith('Lesson_') else 1, p.name))
if not docs: raise SystemExit('没有找到已追踪的技术文档')
entries = subprocess.check_output(['git','ls-tree','-r','-z','--name-only','HEAD'],cwd=ROOT).split(b'\0')
tracked = {p.decode() for p in entries if p}
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(); (OUT / '.nojekyll').touch()

def title(p):
    s=p.read_text(encoding='utf-8')
    m=re.search(r'<title\b[^>]*>(.*?)</title>',s,re.I|re.S)
    return unescape(re.sub(r'\s+',' ',m.group(1)).strip()) if m else p.stem

def label(p):
    name=p.stem.replace('技术总结_', ' · ').replace('总结_', ' · ').replace('_RAG', ' · RAG')
    return name.replace('_', ' ')

def doclink(p):return quote(p.name)

nav=''.join(f'<a href="{doclink(p)}">{escape(label(p))}</a>' for p in docs)
sidebar='''<nav class="course-nav" aria-label="课程文档"><a class="course-brand" href="index.html">▣ &nbsp;LLM Course</a><a class="course-home" href="index.html">← 返回课程目录</a><div class="course-nav-title">学习文档</div>'''+nav+'''<a class="course-github" href="https://github.com/LeonOpus/LLM_Course">查看 GitHub 仓库 ↗</a></nav>'''
css='''<style id="course-navigation">@media(min-width:850px){body{padding-left:245px!important}.course-nav{position:fixed;left:0;top:0;bottom:0;width:230px;overflow:auto;z-index:1000;border-right:1px solid #d8e5ee}}.course-nav{font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif;background:#f8fbff;color:#17395a;padding:18px 14px;box-sizing:border-box;line-height:1.45}.course-nav a{display:block;color:#235782;text-decoration:none;padding:7px 10px;border-radius:6px;font-size:13px;overflow-wrap:anywhere}.course-nav a:hover,.course-nav a:focus{background:#e5f1fc;color:#064e96}.course-nav .course-brand{font-size:18px;font-weight:750;color:#123e67;margin-bottom:12px}.course-nav .course-home{font-size:14px;font-weight:650}.course-nav-title{font-size:12px;font-weight:700;color:#617e98;margin:17px 10px 7px}.course-nav .course-github{margin-top:18px;border-top:1px solid #d8e5ee;padding-top:14px}@media(max-width:849px){.course-nav{position:static;max-height:190px;overflow:auto;border-bottom:1px solid #d8e5ee}.course-nav a:not(.course-brand):not(.course-home):not(.course-github),.course-nav-title{display:none}}</style>'''
attr=re.compile(r'''(\b(?:href|src)\s*=\s*)(["'])(.*?)(\2)''',re.I)

def rewrite(m):
    url=unescape(m.group(3)); u=urlsplit(url)
    if u.scheme or u.netloc or not u.path or u.path.startswith('/') or not u.path.startswith('../'):return m.group(0)
    dest=(DOCS / unquote(u.path)).resolve()
    if not dest.is_relative_to(ROOT):return m.group(0)
    path=dest.relative_to(ROOT).as_posix()
    is_dir=any(p.startswith(path.rstrip('/')+'/') for p in tracked)
    kind='tree' if is_dir else 'blob'
    absolute=f'{BASE}/{kind}/main/{quote(path,safe="/")}'
    absolute=urlunsplit((*urlsplit(absolute)[:3],u.query,u.fragment))
    return m.group(1)+m.group(2)+escape(absolute,quote=True)+m.group(4)

for p in docs:
    html=p.read_text(encoding='utf-8')
    html=attr.sub(rewrite,html)
    html=re.sub(r'</head\s*>',lambda m:css+m.group(0),html,count=1,flags=re.I)
    html=re.sub(r'<body\b[^>]*>',lambda m:m.group(0)+sidebar,html,count=1,flags=re.I)
    (OUT/p.name).write_text(html,encoding='utf-8')

cards=''.join(f'<a class="card" href="{doclink(p)}"><span class="icon">▤</span><span><strong>{escape(label(p))}</strong><small>{escape(title(p))}</small></span><span class="arrow">→</span></a>' for p in docs)
index='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LLM Course 技术文档</title><style>*{box-sizing:border-box}body{margin:0;color:#173653;background:#f5f9fd;font:16px/1.6 system-ui,-apple-system,"Microsoft YaHei",sans-serif}header{background:#fff;border-bottom:1px solid #dce7ef}.bar{max-width:1100px;margin:auto;padding:18px 24px;display:flex;justify-content:space-between;gap:16px;align-items:center}.brand{font-size:20px;font-weight:800;color:#123e67;text-decoration:none}.github{color:#175b99;text-decoration:none;font-weight:600}main{max-width:1100px;margin:auto;padding:52px 24px 80px}.eyebrow{color:#246ca8;font-size:13px;font-weight:750;letter-spacing:.12em}h1{font-size:clamp(30px,5vw,46px);line-height:1.2;color:#12365d;margin:12px 0}p{color:#526d85}h2{font-size:23px;color:#173f68;margin:42px 0 16px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px}.card{display:flex;align-items:flex-start;gap:14px;background:white;border:1px solid #d8e5ef;border-radius:12px;padding:18px;text-decoration:none;color:#174875;min-height:104px;box-shadow:0 2px 8px #1c42680a}.card:hover,.card:focus{border-color:#3887c5;box-shadow:0 6px 18px #1c42681a}.card strong{display:block;font-size:15px;overflow-wrap:anywhere}.card small{display:block;color:#58738b;margin-top:6px;line-height:1.45}.icon{font-size:24px;color:#176cb2}.arrow{margin-left:auto;color:#397aae}footer{margin-top:40px;color:#5d758a;font-size:14px}</style></head><body><header><div class="bar"><a class="brand" href="index.html">▣ &nbsp;LLM Course</a><a class="github" href="https://github.com/LeonOpus/LLM_Course">GitHub 仓库 ↗</a></div></header><main><div class="eyebrow">大模型学习与工程实践</div><h1>LLM Course 技术文档</h1><p>从模型基础、部署测试到 RAG 和 Agent，按课程顺序阅读学习总结。</p><h2>课程与面试资料</h2><div class="cards">'''+cards+'''</div><footer>源码与课程材料请访问 GitHub 仓库。</footer></main></body></html>'''
(OUT/'index.html').write_text(index,encoding='utf-8')
print(f'已生成首页和 {len(docs)} 份阅读页面，输出目录：{OUT}')
