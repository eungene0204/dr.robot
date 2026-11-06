import {isAmdX3d} from '../src/gaming-cpu-policy.mjs';
import {categories} from '../src/catalog.mjs';
import {productIssues} from '../src/product-ontology.mjs';
import {storageRecommendationIssue,minimumStorageGB} from '../src/storage-policy.mjs';
import {benchmarkState,priceState} from '../src/data-policy.mjs';
import {comparePopularity} from '../src/popularity.mjs';
import {collectProduct} from '../pipeline/adapters/danawa.mjs';
import {budgetLimit} from '../src/budget-policy.mjs';
import {recommend} from '../src/engine.mjs';
export function refreshCandidates(snapshot,req){
 const preferred=new Set(['c1','c2','c3','c4','b1','r2','s1','s2','p2','k2','f1','f2']);const result=[];
 for(const category of categories){if(category==='os'&&!req.os)continue;if(category==='gpu'&&req.profile==='office')continue;
  const pool=snapshot.parts.filter(p=>p.category===category&&!p.virtual&&p.danawaPcode&&!productIssues(p).length&&!storageRecommendationIssue(p)&&p.price<budgetLimit(req)&&(!['cpu','gpu'].includes(category)||benchmarkState(p)==='measured')&&(category!=='ssd'||p.capacity>=minimumStorageGB(req))&&(category!=='case'||!req.white||p.color==='white')&&(category!=='board'||p.bios?.length||p.cpuSupport?.length));
  const ranked=[...pool].sort((a,b)=>Number(preferred.has(b.id))-Number(preferred.has(a.id))||comparePopularity(a,b)||a.price-b.price);
  const performance=[...pool].sort((a,b)=>(b.benchmark?.normalizedScore||0)-(a.benchmark?.normalizedScore||0)||a.price-b.price);
  const x3d=[];if(category==='cpu'&&req.profile==='gaming'){const seen=new Set();for(const p of [...pool].filter(isAmdX3d).sort((a,b)=>a.price-b.price)){const cpuId=p.compatibilityCpuId||p.id;if(seen.has(cpuId)||!snapshot.parts.some(b=>b.category==='board'&&b.socket===p.socket&&(b.bios?.includes(cpuId)||b.cpuSupport?.some(s=>s.cpuId===cpuId))))continue;seen.add(cpuId);x3d.push(p);if(x3d.length===2)break;}}
  const picks=[...x3d,...ranked.slice(0,category==='cpu'?3:2),...(['cpu','gpu'].includes(category)?performance.slice(0,2):[])];
  for(const p of picks)if(priceState(p)!=='fresh'&&!result.some(x=>x.id===p.id))result.push(p);
 }
 return result;
}
// Parts the engine would pick if stale prices were still current (null when no plan is feasible); parts whose refresh already failed stay stale; refreshing exactly these keeps budget-fit cheap parts in reach.
export function plannedStaleParts(snapshot,req,settings={},{failed=new Set(),now=new Date().toISOString()}={}){
 const originals=new Map();
 const tentative=snapshot.parts.map(p=>{if(priceState(p)!=='stale'||failed.has(p.id))return p;const copy={...p,priceEvidence:{...p.priceEvidence,observedAt:now}};originals.set(p.id,p);return copy;});
 const result=new Map();const plans=recommend(req,settings,tentative);if(!plans.some(Boolean))return null;
 for(const plan of plans)for(const part of Object.values(plan?.parts||{}))if(originals.has(part.id))result.set(part.id,originals.get(part.id));
 return [...result.values()];
}
export async function refreshPrices(snapshot,req,{client,store,settings={},rounds=3,onProgress=()=>{}}){
 const errors=[];let updated=0;const attempted=new Set();
 const refresh=async part=>{attempted.add(part.id);try{const observation=await collectProduct(client,part);if(!store.acceptProduct({part,price:observation.price}))throw new Error('가격 변동 검수 대기');Object.assign(part,{price:observation.price.amount,priceEvidence:observation.price,observedAt:observation.price.observedAt,inStock:observation.price.availability!=='out-of-stock'});updated++;}catch(error){errors.push({id:part.id,error:error.message})}onProgress({updated,errors});};
 // Refreshed prices can move a plan out of budget, so re-plan until the chosen parts are all current.
 for(let round=0;round<rounds;round++){const planned=plannedStaleParts(snapshot,req,settings,{failed:attempted});
  if(!planned){if(!round)for(const part of refreshCandidates(snapshot,req))await refresh(part);break;}
  if(!planned.length)break;for(const part of planned)await refresh(part);
 }
 return {snapshot,updated,errors};
}
