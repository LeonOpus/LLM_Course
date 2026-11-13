export interface Doc {doc_id:string;name:string;kind:string;status:string;block_count:number;chunk_count:number;error:string|null;stage?:string}
export interface Block {text:string;locator:Record<string,unknown>}
export async function requestJSON(path:string,init:RequestInit={},fetcher:typeof fetch=fetch,timeoutMs=10000):Promise<any>{
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeoutMs);
 const external=init.signal;const onAbort=()=>controller.abort();if(external?.aborted)controller.abort();else external?.addEventListener('abort',onAbort,{once:true});
 try {
  let response:Response;
  try {response=await fetcher('/api'+path,{...init,signal:controller.signal});}
  catch(error){if(controller.signal.aborted)throw error;throw new Error('无法连接后端，请检查服务；提交操作不会自动重试');}
  let data:any;
  try{data=await response.json();}catch(error){if(controller.signal.aborted)throw error;throw new Error('后端没有返回有效 JSON，请检查服务地址');}
  if(!response.ok)throw new Error(typeof data?.detail==='string'?data.detail:`请求失败（HTTP ${response.status}）`);
  return data;
 }catch(error){if(controller.signal.aborted)throw new Error('请求超时，请先刷新文档状态，确认后再决定是否重试');throw error;}
 finally{clearTimeout(timer);external?.removeEventListener('abort',onAbort);}
}
export async function startParse(id:string,fetcher:typeof fetch=fetch):Promise<{doc_id:string;accepted:true}>{
 const data=await requestJSON(`/documents/${encodeURIComponent(id)}/parse`,{method:'POST'},fetcher);
 if(data?.accepted!==true||data?.doc_id!==id)throw new Error('解析受理结果不符合接口契约，请检查后端');
 return data;
}
// checksum: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
/* generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525 */
// cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
// checksum: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
// checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
// checksum: lpf2-18283 lpf2-19E2b
