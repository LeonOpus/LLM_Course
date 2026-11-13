import {pageHashes,pageForHash} from './workspace';
import type {WorkspacePage} from './workspace';
import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';
import {Overview} from './Overview';
import {EvaluationPanel} from './EvaluationPanel';
import {AnswerPanel} from './AnswerPanel';
import {DocumentPanel} from './DocumentPanel';
import './s2.css';
const pages:{page:WorkspacePage;label:string;icon:string;description:string}[]=[
 {page:'知识问答',label:'知识问答',icon:'layout/newchat.svg',description:'从资料中寻找有据可查的答案'},
 {page:'文档',label:'知识库',icon:'layout/repository.svg',description:'上传、解析和管理你的业务资料'},
 {page:'检索调试',label:'检索调试',icon:'chat/search.svg',description:'检查切块与候选，追踪证据在哪里'},
 {page:'质量评估',label:'质量评估',icon:'chat/completed.svg',description:'同题对比，看见提升，也看见退步'},
 {page:'概览',label:'环境检查',icon:'repository/action/setting.svg',description:'查看当前后端状态与配置'},
];
function App(){
 const [page,setPage]=useState<WorkspacePage>(()=>window.location.hash?pageForHash(window.location.hash):'知识问答');
 const [session,setSession]=useState(0);
 useEffect(()=>{const change=()=>setPage(window.location.hash?pageForHash(window.location.hash):'知识问答');window.addEventListener('hashchange',change);return()=>window.removeEventListener('hashchange',change);},[]);
 function navigate(next:WorkspacePage){window.location.hash=pageHashes[next];setPage(next);}
 const current=pages.find(p=>p.page===page)!;
 return <div className="s2-app"><a className="skip-link" href="#workspace-main">跳到主要内容</a>
  <aside className="s2-sidebar"><a className="s2-brand" href="#ask"><img src="/assets/s2/logo.png" alt=""/><span>设备知识库<small>RAG 学习工作台</small></span></a>
   <button className="new-chat" onClick={()=>{setSession(v=>v+1);navigate('知识问答');}}><img src="/assets/s2/layout/newchat.svg" alt=""/>新对话<span>＋</span></button>
   <span className="nav-caption">工作空间</span><nav aria-label="工作区导航">{pages.map(item=><button key={item.page} aria-current={page===item.page?'page':undefined} onClick={()=>navigate(item.page)}><img src={'/assets/s2/'+item.icon} alt=""/>{item.label}</button>)}</nav>
   <div className="sidebar-note"><span className="note-orbit">↗</span><strong>从资料到可信答案</strong><p>核对来源 · 对比策略<br/>让每一次优化都有证据</p></div>
   <div className="sidebar-footer"><span className="workspace-avatar">知</span><div>课程实操工作区<small>设备产品与售后</small></div></div>
  </aside>
  <div className="s2-workspace"><header className="workspace-header"><div><span>工作空间</span><b>/</b><strong>{current.label}</strong></div><span className="workspace-badge">RAG · 实操项目</span></header>
   <main id="workspace-main" tabIndex={-1} className={'workspace-main '+(page==='知识问答'?'is-chat':'is-page')}>
    {page==='知识问答'?<AnswerPanel key={session}/>:page==='文档'?<DocumentPanel/>:page==='检索调试'?<DocumentPanel view="retrieval"/>:page==='质量评估'?<EvaluationPanel/>:<Overview/>}
   </main>
   {page!=='知识问答'&&<footer className="workspace-footer">设备知识库 · {current.description}</footer>}
  </div>
 </div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
/* revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// cache: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
/* revision: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72 */
// cache: lpf2-18283 lpf2-19E2b
