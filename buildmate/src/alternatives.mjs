import {storageRecommendationIssue} from './storage-policy.mjs';
import {validateBuild,total} from './engine.mjs';
import {usablePart,priceState,benchmarkState} from './data-policy.mjs';

export function partSelectableForDraft(part){
 if(part?.category==='cpu'&&part.dataMode==='live')return priceState(part)==='fresh'&&part.inStock!==false&&typeof part.socket==='string'&&Number.isFinite(part.watts);
 return usablePart(part);
}
// compatibleIds: ids an external engine (pcquote) found compatible and usable; its rules replace validateBuild here.
export function alternativeOptions(catalog,category,plan,req,settings={},{compatibleIds=null}={}){
 return catalog.filter(p=>!storageRecommendationIssue(p)&&p.category===category&&(category!=='ssd'||!/외장|external|USB|케이스|인클로저/i.test(p.name))).map(part=>{
  const external=compatibleIds?{label:'호환성(pcquote)',ok:compatibleIds.has(part.id),detail:compatibleIds.has(part.id)?'pcquote 호환 규칙 통과':'pcquote 호환·사양 조건 미충족'}:null;
  const checks=external?[external]:validateBuild({...plan.parts,[category]:part},req);
  const reasons=checks.filter(c=>c.ok!==true).map(c=>`${c.label}${c.ok===null?' 확인 필요':' 조건 불충족'}`);
  if(!usablePart(part)){
   if(part.dataMode==='live'){
    if(!['fresh','not-applicable'].includes(priceState(part)))reasons.push('가격 갱신 필요');
    if(!['measured','not-applicable'].includes(benchmarkState(part)))reasons.push('실측 벤치마크 확인 필요');
   }else reasons.push('부품 데이터 확인 필요');
   if(part.inStock===false)reasons.push('판매 상태 확인 필요');
  }
  const compatible=checks.every(c=>c.ok===true);
  const platformCompatible=checks.filter(c=>['CPU 소켓','BIOS 지원','메모리 규격'].includes(c.label)).every(c=>c.ok===true);
  const canSelect=true;
  return {part,checks,reasons,canSelect,selectable:usablePart(part)&&compatible,total:Number.isFinite(part.price)?total({...plan.parts,[category]:part},settings):null};
 });
}
export function compareSpecifications(a,b){
 const p=a.part,q=b.part;
 const keys={cpu:['benchmark.normalizedScore','cores'],gpu:['benchmark.normalizedScore','vram'],ram:['capacity','speedMHz'],ssd:['capacity','readMBs','writeMBs'],psu:['capacity'],case:['gpuLength','coolerHeight'],cooler:['coolingWatts']}[p.category]||[];
 const value=(part,key)=>key.split('.').reduce((v,k)=>v?.[k],part);
 for(const key of keys){const diff=(value(q,key)??0)-(value(p,key)??0);if(diff)return diff;}
 return (p.price??Infinity)-(q.price??Infinity)||p.name.localeCompare(q.name);
}
