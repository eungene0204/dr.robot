export const POPULARITY_MAX_AGE_HOURS=48;
export function popularityRank(part,now=Date.now()){
 const p=part?.popularity;if(!p||p.category!==part.category||p.sort!=='BEST'||p.scope!=='category-family'||!Number.isSafeInteger(p.rank)||p.rank<1||!/^https:\/\/prod\.danawa\.com\/list\/\?/.test(p.sourceUrl||''))return null;
 const at=Date.parse(p.observedAt);return Number.isFinite(at)&&at<=now+300000&&now-at<=POPULARITY_MAX_AGE_HOURS*3600000?p.rank:null;
}
export function comparePopularity(a,b){const x=popularityRank(a),y=popularityRank(b);return (x??Infinity)-(y??Infinity)||0;}
export function popularitySummary(parts){const values=Object.values(parts).filter(p=>p&&!p.virtual&&p.category!=='os');const ranks=values.map(p=>popularityRank(p)).filter(r=>r!==null);return {known:ranks.length,total:values.length,penalty:ranks.reduce((n,r)=>n+Math.log1p(r),0),source:'다나와 카테고리 인기상품순',scope:'category-family'};}
export function compareBuildPopularity(a,b){const x=popularitySummary(a.parts),y=popularitySummary(b.parts);return y.known-x.known||(x.known?x.penalty-y.penalty:0);}
