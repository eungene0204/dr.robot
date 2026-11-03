export const PRICE_MAX_AGE_HOURS=24;
export const BENCHMARK_MAX_AGE_DAYS=45;
export function isFresh(when,maxHours,now=Date.now()){const at=Date.parse(when);return Number.isFinite(at)&&at<=now+300000&&now-at<=maxHours*3600000;}
export function priceState(part,now=Date.now()){
 if(part.virtual)return 'not-applicable';
 if(!Number.isFinite(part.price)||part.price<=0||!part.priceEvidence?.sourceUrl)return 'missing';
 return isFresh(part.priceEvidence.observedAt,PRICE_MAX_AGE_HOURS,now)?'fresh':'stale';
}
export function benchmarkState(part,now=Date.now()){
 if(!['cpu','gpu'].includes(part.category)||part.virtual)return 'not-applicable';
 const b=part.benchmark;
 if(!b||!Number.isFinite(b.score)||b.score<=0||b.samples<3||!b.sourceUrl)return 'missing';
 return isFresh(b.observedAt,BENCHMARK_MAX_AGE_DAYS*24,now)?'measured':'stale';
}
export function usablePart(part,now=Date.now()){
 if(part.dataMode!=='live')return part.verified&&part.inStock&&Number.isFinite(part.price)&&part.price>=0;
 if(part.virtual)return true;
 return priceState(part,now)==='fresh'&&part.inStock!==false&&(!['cpu','gpu'].includes(part.category)||benchmarkState(part,now)==='measured');
}
export function hydrateSnapshot(snapshot,now=Date.now()){
 if(snapshot?.schemaVersion!==2||snapshot?.mode!=='live'||!Array.isArray(snapshot.parts)||snapshot.parts.length>2000)throw new Error('실제 데이터 스냅샷 형식이 올바르지 않습니다.');
 const ids=new Set();const categories=new Set(['cpu','board','ram','gpu','ssd','psu','case','cooler','os']);
 for(const p of snapshot.parts){if(!p||typeof p.id!=='string'||ids.has(p.id)||!categories.has(p.category)||typeof p.name!=='string')throw new Error('카탈로그 식별자 오류');ids.add(p.id);}
 const parts=snapshot.parts.map(p=>({...p,dataMode:'live',priceStatus:priceState(p,now),benchmarkStatus:benchmarkState(p,now)}));
 return {...snapshot,parts,coverage:{...snapshot.coverage,freshPrices:parts.filter(p=>!p.virtual&&priceState(p,now)==='fresh').length,measuredBenchmarks:parts.filter(p=>benchmarkState(p,now)==='measured').length,ready:parts.filter(p=>!p.virtual&&usablePart(p,now)).length,stalePrices:parts.filter(p=>priceState(p,now)==='stale').length,missingPrices:parts.filter(p=>priceState(p,now)==='missing').length}};
}
