export type Fetcher = (url: string, init?: RequestInit) => Promise<Response>;
export type Health = {status:'ok';service:string;verification:'configuration_only';configured:{bailian:boolean;docmind:boolean;rerank:boolean};models:{chat:string;embedding:string;dimension:number};supported_extensions:string[];strategies:string[];context_configuration:{context_policy:'baseline'|'parent_section'};index_configuration:{chunk_strategy:string;collection:string};query_configuration:{retrieval_mode:string;query_rewrite:string;generation_policy:string}};
const object=(v:unknown):v is Record<string,unknown>=>v!==null&&typeof v==='object'&&!Array.isArray(v);
export function parseHealth(p:unknown):Health {
 if(!object(p)||p.status!=='ok'||p.service!=='rag-backend'||p.verification!=='configuration_only'||!object(p.configured)||['bailian','docmind','rerank'].some(k=>typeof (p.configured as Record<string,unknown>)[k]!=='boolean'))throw new Error('后端响应格式不符合公开配置契约');
 if(!object(p.models)||typeof p.models.chat!=='string'||typeof p.models.embedding!=='string'||!Number.isInteger(p.models.dimension)||Number(p.models.dimension)<1||!Array.isArray(p.supported_extensions)||!p.supported_extensions.every(v=>typeof v==='string')||!Array.isArray(p.strategies))throw new Error('模型或格式不符合公开配置契约');
 if(!object(p.index_configuration)||['chunk_strategy','collection'].some(k=>typeof (p.index_configuration as Record<string,unknown>)[k]!=='string')||!object(p.query_configuration)||['retrieval_mode','query_rewrite','generation_policy'].some(k=>typeof (p.query_configuration as Record<string,unknown>)[k]!=='string'))throw new Error('索引或查询配置不符合契约');
 if(!object(p.context_configuration)||!['baseline','parent_section'].includes(String(p.context_configuration.context_policy)))throw new Error('上下文配置不符合契约');
 return p as Health;
}
export async function fetchHealth(fetcher: Fetcher = fetch, timeoutMs = 5000): Promise<Health> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    let response: Response;
    try {
      response = await fetcher('/api/health', {method: 'GET', signal: controller.signal});
    } catch {
      if (controller.signal.aborted) throw new Error('请求超时，请检查后端并重试');
      throw new Error('无法连接后端，请检查网络和后端终端');
    }
    if (!response.ok) throw new Error(`后端请求失败：HTTP ${response.status}`);
    let payload: unknown;
    try { payload = await response.json(); }
    catch {
      if (controller.signal.aborted) throw new Error('响应正文超时，请重试');
      throw new Error('后端没有返回有效 JSON');
    }
    return parseHealth(payload);
  } finally { clearTimeout(timer); }
}
/* generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222 */
/* revision: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368 */
// cache: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
/* generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc */
// cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
/* revision: lpf2-18283 lpf2-19E2b */
