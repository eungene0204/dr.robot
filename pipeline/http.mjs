import robotsParser from 'robots-parser';
import {mkdir,readFile,writeFile,rename} from '../backend/document-files.mjs';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
export const AGENT='DrRobot/0.3 (+PC-component-price-monitor; no AI training)';
const allowedHosts=new Set(['prod.danawa.com','search.danawa.com','openapi.naver.com','opendata.blender.org']);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
export class SourceError extends Error {constructor(message,code='source_error'){super(message);this.code=code;}}
export class SourceClient {
 constructor({cacheDir='backend/data/cache',fetchImpl=fetch,minDelayMs=2000,cacheTtlMs=0}={}){this.cacheDir=resolve(cacheDir);this.fetch=fetchImpl;this.minDelayMs=minDelayMs;this.cacheTtlMs=cacheTtlMs;this.robots=new Map();this.next=new Map();}
 async raw(url,options={}){
  const u=new URL(url);if(u.protocol!=='https:'||!allowedHosts.has(u.hostname))throw new SourceError('허용되지 않은 수집 URL','invalid_url');
  for(let attempt=0;attempt<3;attempt++){
   try{const response=await this.fetch(url,{...options,redirect:'error',headers:{'User-Agent':AGENT,...options.headers},signal:AbortSignal.timeout(30000)});
    if([429,500,502,503,504].includes(response.status)&&attempt<2){const retry=Number(response.headers.get('retry-after'));if(Number.isFinite(retry)&&retry>60)throw new SourceError('Retry-After가 길어 이번 실행을 보류합니다.','rate_limited');await sleep(Number.isFinite(retry)&&retry>0?retry*1000:1000*2**attempt);continue;}
    if(!response.ok&&response.status!==304)throw new SourceError(`수집 응답 HTTP ${response.status}`,'http_'+response.status);
    return response;
   }catch(e){if(e instanceof SourceError||attempt===2)throw e;await sleep(1000*2**attempt);}
  }
 }
 async policy(url){const u=new URL(url);if(this.robots.has(u.origin))return this.robots.get(u.origin);const r=await this.raw(u.origin+'/robots.txt');const text=await r.text();const policy=robotsParser(u.origin+'/robots.txt',text);this.robots.set(u.origin,policy);return policy;}
 async text(url,{maxBytes=8_000_000,headers={},api=false,ttlMs=this.cacheTtlMs}={}){
  const u=new URL(url);const key=createHash('sha256').update(url).digest('hex');await mkdir(this.cacheDir,{recursive:true});const path=resolve(this.cacheDir,key+'.json');let cached;
  // Requests with credentials are never persisted in cache keys or headers.
  try{cached=JSON.parse(await readFile(path,'utf8'));}catch{}
  if(ttlMs&&cached&&Date.now()-Date.parse(cached.fetchedAt)<ttlMs)return cached;
  let delay=this.minDelayMs;
  if(!api){const policy=await this.policy(url);if(policy.isAllowed(url,'DrRobot')===false)throw new SourceError('robots.txt가 이 경로의 수집을 제한합니다.','robots_denied');delay=Math.max(delay,(policy.getCrawlDelay('DrRobot')||0)*1000);}
  const wait=Math.max(0,(this.next.get(u.origin)||0)-Date.now());if(wait)await sleep(wait);this.next.set(u.origin,Date.now()+delay);
  const response=await this.raw(url,{headers:{...headers,...(cached?.etag?{'If-None-Match':cached.etag}:{}),...(cached?.lastModified?{'If-Modified-Since':cached.lastModified}:{})}});
  const fetchedAt=new Date().toISOString();let text=cached?.text;
  if(response.status!==304){let bytes=0;const chunks=[];for await(const chunk of response.body){bytes+=chunk.length;if(bytes>maxBytes){await response.body.cancel().catch(()=>{});throw new SourceError('원문 크기 제한을 초과했습니다.','too_large');}chunks.push(Buffer.from(chunk));}text=Buffer.concat(chunks).toString('utf8');}
  if(typeof text!=='string')throw new SourceError('캐시 없는 304 응답','invalid_cache');
  const data={url,text,fetchedAt,hash:createHash('sha256').update(text).digest('hex'),etag:response.headers.get('etag')||cached?.etag,lastModified:response.headers.get('last-modified')||cached?.lastModified};
  await writeFile(path+'.tmp',JSON.stringify(data));await rename(path+'.tmp',path);return data;
 }
}
