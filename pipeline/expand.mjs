import {readFile,writeFile,mkdir,rename,open,unlink} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {SourceClient} from './http.mjs';
import {parseSearch,collectProduct} from './adapters/danawa.mjs';
import {PipelineStore} from './store.mjs';
import {collectionWindow} from './window.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const read=async(path,fallback)=>{try{return JSON.parse(await readFile(path,'utf8'))}catch(e){if(e.code==='ENOENT'&&fallback!==undefined)return fallback;throw e}};
const write=async(path,data)=>{await mkdir(dirname(path),{recursive:true});await writeFile(path+'.tmp',JSON.stringify(data,null,2)+'\n');await rename(path+'.tmp',path)};
export function benchmarkName(category,name){
 if(category==='cpu'){
  const amd=name.match(/라이젠\s*([3579])(?:-\d+세대)?\s*(\d{4}[A-Z0-9]*)/i);if(amd)return `AMD Ryzen ${amd[1]} ${amd[2].toUpperCase()}`;
  const intel=name.match(/코어\s*(?:울트라\s*)?i?([3579])(?:-\d+세대|\s*시리즈\d+)?\s*\(?([1-9]\d{2,4}[A-Z]*)(?:\s*(Plus))?/i);if(intel)return /울트라/.test(name)?`Intel Core Ultra ${intel[1]} ${intel[2]}${intel[3]?' Plus':''}`:`Intel Core i${intel[1]}-${intel[2]}`;
 }
 if(category==='gpu'){
  const n=name.match(/(?:RTX|GTX)\s*(\d{4})\s*(Ti)?\s*(SUPER)?/i);if(n)return `NVIDIA GeForce ${n[0].replace(/\s+/g,' ').replace(/(RTX|GTX)\s*/i,'$1 ').replace(/(\d)(Ti)/i,'$1 $2').trim()}`;
  const a=name.match(/RX\s*(\d{4})\s*(XTX|XT|GRE)?/i);if(a)return `AMD Radeon RX ${a[1]}${a[2]?' '+a[2].toUpperCase():''}`;
 }
 return undefined;
}
export function validDiscovered(part){
 if(/중고|리퍼|렌탈|대여|완본체|조립PC|미니PC|노트북|서버용|ECC|SO-DIMM|SODIMM|등록 대행|해외구매|해외직구/i.test(part.name))return false;
 if(part.sourceCategory===part.category&&(part.category!=='cooler'||/CPU.*쿨러/i.test(part.productType||'')))return true;
 const required={cpu:['socket','cores'],board:['socket','ddr','form','slots'],ram:['ddr','capacity'],gpu:['vram','length'],ssd:['capacity','m2'],psu:['capacity','connectors'],case:['forms','gpuLength','coolerHeight'],cooler:['sockets','height']};
 return (required[part.category]||[]).length>0&&required[part.category].every(key=>part[key]!==null&&part[key]!==undefined);
}
export const canAdvance=(cursor,config)=>!cursor?.done&&(config.maxPagesPerQuery==null||cursor.page<=config.maxPagesPerQuery);
export async function expandCatalog({daily=false,client=new SourceClient(),configPath=resolve(root,'pipeline/config/discovery.json'),registryPath=resolve(root,'pipeline/config/products.json'),dataDir=resolve(root,'backend/data'),onProgress=console.log}={}){
 await mkdir(dataDir,{recursive:true});const lockPath=resolve(dataDir,'expansion.lock');const lock=await open(lockPath,'wx');
 let store;try{
 const config=await read(configPath);const registry=await read(registryPath);const statePath=resolve(dataDir,'discovery-state.json');const state=await read(statePath,{queries:{},candidates:{}});state.queries??={};state.candidates??={};if(state.parserVersion!==3){for(const p of Object.values(state.candidates)){if(p.status==='rejected')p.status='pending';}state.parserVersion=3;}
 if(state.scopeVersion!==4){if(!state.scopeVersion||state.scopeVersion<3)state.queries={};for(const candidate of Object.values(state.candidates)){if(candidate.status==='rejected')candidate.status='pending';}state.scopeVersion=4;}state.collectionWindow=collectionWindow(new Date(),config.releaseWindowYears||2);state.collectionWindow.complete=false;
 store=new PipelineStore(resolve(dataDir,'pipeline.db'));
 const known=new Map(registry.products.map(p=>[String(p.danawaPcode),p]));const summary={pages:0,discovered:0,added:0,rejected:0,errors:0};
 const progress=async()=>{state.updatedAt=new Date().toISOString();state.summary=summary;await write(statePath,state);await onProgress(JSON.stringify({stage:'expand',...summary,registered:registry.products.length}))};
 // Save each search page before collecting products; interrupted work resumes from this queue.
 for(const seed of config.queries){
  const key=seed.category+':'+seed.query;const cursor=state.queries[key]||{page:1,seen:[]};
  if(seed.source==='category-index'){
   if(!cursor.done||daily){try{const url=`https://prod.danawa.com/list/?cate=${seed.categoryCode}`;const page=await client.text(url);const found=parseSearch(page.text);if(!found.length)throw new Error('카테고리 공개 HTML에서 상품을 확인할 수 없습니다.');summary.pages++;for(const candidate of found){if(!known.has(candidate.pcode)&&!state.candidates[candidate.pcode]){state.candidates[candidate.pcode]={...candidate,category:seed.category,status:'pending',searchUrl:url};summary.discovered++;}}cursor.done=true;cursor.indexOnly=true;cursor.coverageLimited=true;cursor.stopReason='public-category-index';}catch(e){summary.errors++;cursor.error=e.message;}}
   state.queries[key]=cursor;await progress();continue;
  }
  if(daily){try{const url=new URL('https://search.danawa.com/');url.searchParams.set('query',seed.query);url.searchParams.set('page','1');url.searchParams.set('sort','dateDESC');const page=await client.text(url.href);summary.pages++;for(const candidate of parseSearch(page.text)){if(!known.has(candidate.pcode)&&!state.candidates[candidate.pcode]){state.candidates[candidate.pcode]={...candidate,category:seed.category,status:'pending',searchUrl:url.href};summary.discovered++;}}}catch(e){summary.errors++;cursor.error=e.message;}}
  if(cursor.done){state.queries[key]=cursor;await progress();continue;}
  for(let step=0;step<(config.pagesPerPass||1)&&canAdvance(cursor,config);step++){
   try{const url=new URL('https://search.danawa.com/');url.searchParams.set('query',seed.query);url.searchParams.set('page',cursor.page);
    const page=await client.text(url.href);const found=parseSearch(page.text);const fresh=found.filter(p=>!cursor.seen.includes(p.pcode));
    summary.pages++;if(!fresh.length){if(!found.length&&cursor.page===1)throw new Error('공개 검색 페이지의 결과를 확인하지 못했습니다. 수집 완료로 처리하지 않습니다.');cursor.done=true;cursor.stopReason=found.length?'repeated-page':'empty-page';break;}
    for(const candidate of fresh){cursor.seen.push(candidate.pcode);if(!known.has(candidate.pcode)&&!state.candidates[candidate.pcode]){state.candidates[candidate.pcode]={...candidate,category:seed.category,status:'pending',searchUrl:url.href};summary.discovered++;}}
    cursor.page++;
   }catch(e){summary.errors++;cursor.error=e.message;break;}
  }
  state.queries[key]=cursor;await progress();
 }
 const cutoffMonth=state.collectionWindow.start.slice(0,7);const priority=candidate=>candidate.listingMonth?(candidate.listingMonth>=cutoffMonth?0:2):1;
 for(const candidate of Object.values(state.candidates).sort((a,b)=>priority(a)-priority(b)||Number(b.pcode)-Number(a.pcode))){
  if(known.has(candidate.pcode)||candidate.status==='rejected')continue;
  if(candidate.status==='failed'&&Date.now()-Date.parse(candidate.at||0)<3600000)continue;
  const product={id:'dw-'+candidate.pcode,category:candidate.category,name:candidate.name,danawaPcode:candidate.pcode,discoveredAt:state.updatedAt,discoverySource:candidate.searchUrl};
  try{
   const observation=await collectProduct(client,product,{allowMissingPrice:true});candidate.listingMonth=observation.part.listingMonth;candidate.dateStatus=observation.part.listingMonth?'registration-month':'unknown';
   if(!validDiscovered(observation.part)){candidate.status='rejected';candidate.reason='품목 불일치 또는 필수 스펙 누락';summary.rejected++;}
   else{
    product.name=observation.part.name;product.benchmarkName=benchmarkName(product.category,product.name);
    const sameChip=registry.products.find(p=>product.benchmarkName&&p.benchmarkName===product.benchmarkName);
    if(sameChip)product.compatibilityCpuId=sameChip.compatibilityCpuId||sameChip.id;
    Object.assign(observation.part,product);
    if(!observation.price)store.recordProduct(observation.part);
    if(!observation.price||store.acceptProduct(observation)){registry.products.push(product);known.set(candidate.pcode,product);candidate.status='collected';candidate.priceStatus=observation.price?'priced':'unavailable';summary.added++;const latest=await read(registryPath);for(const added of latest.products)if(!registry.products.some(p=>p.id===added.id)){registry.products.push(added);known.set(String(added.danawaPcode),added);}await write(registryPath,registry);}else{candidate.status='failed';candidate.reason='가격 검수 필요';}
   }
  }catch(e){candidate.status='failed';candidate.reason=e.message;summary.errors++;}
  candidate.at=new Date().toISOString();await progress();
 }
 return summary;
 }finally{store?.close();await lock.close();await unlink(lockPath);}
}
if(process.argv[1]===fileURLToPath(import.meta.url))await expandCatalog();
