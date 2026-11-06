import {isAmdX3d} from './gaming-cpu-policy.mjs';
import {comparePopularity,compareBuildPopularity,popularityRank} from './popularity.mjs';
import {budgetLimit,validBudget,unlimitedBudgetRequested} from './budget-policy.mjs';
import {productIssues} from './product-ontology.mjs';
import {selectProposals} from './proposal-objectives.mjs';
import {evaluatePerformance} from './workload-evidence.mjs';
import {validate,compatibilityDependencies} from './compatibility.mjs';
export {validate} from './compatibility.mjs';
import {storageIssue,storageRecommendationIssue,minimumStorageGB} from './storage-policy.mjs';
import {catalog,categories} from './catalog.mjs';
import {usablePart} from './data-policy.mjs';
export const money=n=>new Intl.NumberFormat('ko-KR').format(n)+'원';
export function explicitBudget(text){
 const matches=[...text.matchAll(/(\d[\d,]*(?:\.\d+)?)\s*(만\s*원?|원)/g)];
 const last=matches.at(-1);if(!last)return null;
 return Math.round(Number(last[1].replaceAll(',',''))*(last[2].startsWith('만')?10000:1));
}
export function parseRequirement(text,options={}) {
 const statedBudget=explicitBudget(text);
 const requests=text.split(/\n추가 요청:\s*/);
 const detectProfile=value=>/편집|프리미어|다빈치|렌더|3D/i.test(value)?'editing':/로컬|딥러닝|LLM|개발|AI/i.test(value)?'ai':/사무|엑셀|학습|POS/i.test(value)?'office':/게임|게이밍|배그|롤|gaming/i.test(value)?'gaming':/인터넷|웹\s*서핑|웹\s*브라우|문서|인강|온라인\s*강의|유튜브|동영상\s*시청/i.test(value)?'office':null;
 const profile=requests.map(detectProfile).filter(Boolean).at(-1)??'gaming';
 const resolution=requests.map(value=>/4k/i.test(value)?'4K':/FHD|1080/i.test(value)?'FHD':/QHD|1440/i.test(value)?'QHD':detectProfile(value)==='office'?'FHD':null).filter(Boolean).at(-1)??'QHD';
 return {text,profile,budget:statedBudget,resolution,white:/화이트|흰색/.test(text),wifi:/와이파이|무선|wifi/i.test(text),os:/윈도우|windows|OS 포함/i.test(text),allowOver:false,...options,...(unlimitedBudgetRequested(text)?{budget:null,allowOver:false}:{}),budgetSource:unlimitedBudgetRequested(text)?'unlimited':options.budget!=null?(statedBudget!==null?'text':'manual'):statedBudget!==null?'text':'unspecified'};
}
export function validateBuild(parts,req){
 const checks=validate(parts);if(checks.some(c=>c.label==='필수 부품'))return checks;
 const add=(label,ok,detail)=>checks.push({label,ok:Boolean(ok),detail});
 add('제품 유형·필수 속성',categories.every(c=>parts[c].category===c&&!productIssues(parts[c]).length),'제품 역할과 필수 속성 검증');
 add('저장장치 분류',!storageIssue(parts.ssd),storageIssue(parts.ssd)||'저장 용량이 확인된 내부 드라이브');
 add('스토리지 인터페이스',!storageRecommendationIssue(parts.ssd),storageRecommendationIssue(parts.ssd)||'NVMe 스토리지');
 add('케이스 선호',!req.white||parts.case.color==='white','고객이 지정한 필수 색상');
 add('무선 네트워크',!req.wifi||parts.board.wifi,'Wi-Fi 필수 조건');
 add('운영체제',!req.os||parts.os.id==='o1','정품 OS 포함 조건');
 add('용도 최소 조건',req.profile==='office'||(parts.gpu.id!=='g0'&&parts.ram.capacity>=32),'게임·편집·AI: 외장 GPU와 32GB 이상');
 add('AI VRAM',req.profile!=='ai'||parts.gpu.vram>=16,'로컬 AI: VRAM 16GB 이상');
 add('주 저장 공간',parts.ssd.capacity>=minimumStorageGB(req),`최소 ${minimumStorageGB(req)}GB NVMe 주 드라이브`);
 add('편집 저장 공간',req.profile!=='editing'||parts.ssd.capacity>=2000,'영상 편집: SSD 2TB 이상');
 return checks;
}
export const total=(parts,settings={})=>Object.values(parts).reduce((s,p)=>s+p.price,0)+Number(settings.assembly||0);
export function performance(parts,req){return evaluatePerformance(parts,req).score;}
// Every proposed build is validated as a complete assembly before it can be shown.
export function assembleBuild(parts,req,settings={}){
 const checks=validateBuild(parts,req);
 if(!checks.every(check=>check.ok===true))return null;
 const performanceBasis=evaluatePerformance(parts,req);
 if(req.performanceMode==='measured'&&performanceBasis.score===null)return null;
 return {parts:{...parts},total:total(parts,settings),checks,performance:performanceBasis.score,performanceBasis,dataMode:parts.cpu.dataMode||'demo'};
}
export function recommend(req,settings={},items=catalog){
 if(!validBudget(req))throw new Error('예산은 20만~2,000만 원 사이로 입력해 주세요.');
 if(req.performanceMode==='measured'){
  const byId=new Map(items.map(p=>[p.id,p]));const unique=new Map();
  for(const cpu of items.filter(p=>p.category==='cpu'))for(const measurement of cpu.workloadMeasurements||[]){
   const parts=Object.fromEntries(categories.map(c=>[c,byId.get(measurement.configuration?.[c])]));
   if(categories.some(c=>!parts[c]||parts[c].category!==c||!usablePart(parts[c])||settings.excludedBrands?.includes(parts[c].brand)))continue;
   const build=assembleBuild(parts,req,settings);if(build&&build.total<=budgetLimit(req))unique.set(categories.map(c=>parts[c].id).join('|'),build);
  }
  return selectProposals([...unique.values()],req,{method:'measured-configurations',guarantee:'matching-measurements-only',catalogCount:items.length});
 }
 const pools=categories.map(c=>items.filter(p=>p.category===c&&usablePart(p)&&!settings.excludedBrands?.includes(p.brand)));
 pools[0]=pools[0].filter(p=>req.profile!=='office'||p.igpu);
 pools[2]=pools[2].filter(p=>p.capacity>=(req.profile==='office'?16:32));
 pools[3]=pools[3].filter(p=>req.profile==='office'?p.id==='g0':p.id!=='g0'&&(req.profile!=='ai'||p.vram>=16));
 pools[4]=pools[4].filter(p=>p.capacity>=minimumStorageGB(req)&&!/외장|external|USB|케이스|인클로저/i.test(p.name)&&(req.profile!=='editing'||p.capacity>=2000));
 pools[6]=pools[6].filter(p=>!req.white||p.color==='white');
 pools[1]=pools[1].filter(p=>!req.wifi||p.wifi);
 pools[8]=pools[8].filter(p=>req.os?!p.virtual&&p.included!==false:p.id==='o0');
 // Collapse equivalent candidates by fields used by this recommendation model, never by price rank.
 const fields={cpu:['compatibilityCpuId','socket','watts','igpu','score','benchmark','cpuSupport','installedBios','revision'],board:['socket','ddr','form','slots','maxRam','m2','wifi','bios','cpuSupport','installedBios','revision'],ram:['ddr','capacity','sticks'],gpu:['virtual','watts','vram','length','thickness','thicknessMm','connector','connectorCount','minPsu','score','benchmark'],ssd:['capacity','m2','readMBs','writeMBs'],psu:['capacity','connectors','connectorCounts','form'],case:['forms','gpuLength','gpuThickness','expansionSlots','coolerHeight','color','psuForms'],cooler:['sockets','height','coolingWatts','color'],os:['id']};
 for(let i=0;i<pools.length;i++){
  const unique=new Map();for(const part of pools[i].sort((a,b)=>comparePopularity(a,b)||a.price-b.price)){const key=JSON.stringify([...(categories[i]==='cpu'?[part.compatibilityCpuId||part.id]:[]),...fields[categories[i]].map(k=>k==='benchmark'?{version:part.benchmark?.version,normalizedScore:part.benchmark?.normalizedScore}:part[k])]);if(!unique.has(key))unique.set(key,part);}
  pools[i]=[...unique.values()].sort((a,b)=>a.price-b.price);
 }
 // A higher-priced PSU with no capacity/connector advantage cannot improve this model.
 const psuKey=p=>JSON.stringify([p.form||'ATX',[...(p.connectors||[])].sort(),p.connectorCounts||null]);
 pools[5]=pools[5].filter(part=>!pools[5].some(other=>other!==part&&comparePopularity(other,part)<=0&&psuKey(other)===psuKey(part)&&other.price<=part.price&&other.capacity>=part.capacity&&(other.price<part.price||other.capacity>part.capacity)));
 // Keep board-specific GPU dimensions, but discard strictly dominated variants of the same measured chip.
 const gpuKey=p=>JSON.stringify([Boolean(p.virtual),p.benchmark?.version,p.benchmark?.normalizedScore,p.score,p.vram,p.connector,p.connectorCount]);
 const gpuMetrics=['watts','length','thicknessMm','minPsu'];
 pools[3]=pools[3].filter(part=>!pools[3].some(other=>other!==part&&comparePopularity(other,part)<=0&&gpuKey(other)===gpuKey(part)&&other.price<=part.price&&gpuMetrics.every(k=>Number.isFinite(part[k])&&Number.isFinite(other[k])&&other[k]<=part[k])&&(other.price<part.price||gpuMetrics.some(k=>other[k]<part[k]))));
 // Storage with a higher price and no capacity or speed advantage cannot
 // improve any plan. Keep every price/specification tradeoff in the search.
 pools[4]=pools[4].filter(part=>!pools[4].some(other=>other!==part&&comparePopularity(other,part)<=0&&other.m2===part.m2&&other.price<=part.price&&other.capacity>=part.capacity&&['readMBs','writeMBs'].every(k=>!Number.isFinite(part[k])||(Number.isFinite(other[k])&&other[k]>=part[k]))&&(other.price<part.price||other.capacity>part.capacity||['readMBs','writeMBs'].some(k=>Number.isFinite(other[k])&&other[k]>(part[k]??0)))));
 const depends=compatibilityDependencies;
 const placeholders=Object.fromEntries(categories.map(c=>[c,{}]));
 const compatibilityCache=new Map();
 const partialCompatible=(parts,index)=>{
  const newlyComplete=Object.entries(depends).filter(([,keys])=>keys.includes(categories[index])&&keys.every(c=>parts[c]));
  let checks;
  for(const [label,keys] of newlyComplete){
   const key=JSON.stringify([label,...keys.map(c=>parts[c].id)]);
   if(!compatibilityCache.has(key)){checks??=validate({...placeholders,...parts});const check=checks.find(c=>c.label===label);compatibilityCache.set(key,check?check.ok===true:label==='파워 장착 규격');}
   if(!compatibilityCache.get(key))return false;
  }
  return true;
 };
 const minimumRemaining=Array(categories.length+1).fill(0);for(let i=categories.length-1;i>=0;i--)minimumRemaining[i]=minimumRemaining[i+1]+(pools[i][0]?.price??Infinity);
 let visited=0;
 const cap=Math.floor(budgetLimit(req));
 let combos=[];
 const leastCost=new Map();
 function visit(i,parts,cost){
  // Keep storage capacity and speed distinct when pruning equivalent builds.
  // After the PSU check its identity cannot affect future compatibility tests.
  if(i>=6){const key=JSON.stringify([Object.values(parts).map(p=>popularityRank(p)),i,parts.cpu.id,i<7?parts.board.id:null,parts.gpu.id,parts.ram.capacity,parts.ssd.capacity,parts.ssd.readMBs,parts.ssd.writeMBs,i===7?parts.case.id:null,i===6?(parts.psu.form||'ATX'):null]);const prior=leastCost.get(key);if(prior!==undefined&&prior<=cost)return;leastCost.set(key,cost);}
  if(++visited>500000)throw new Error('후보 조합이 너무 많습니다. 카탈로그나 필수 조건으로 후보를 줄여 주세요.');
  if(cost+minimumRemaining[i]+Number(settings.assembly||0)>cap)return;
  if(i===categories.length){const build=assembleBuild(parts,req,settings);if(build)combos.push(build);return;}
  for(const p of pools[i]){if(cost+p.price+minimumRemaining[i+1]+Number(settings.assembly||0)>cap)break;const next={...parts,[categories[i]]:p};if(partialCompatible(next,i))visit(i+1,next,cost+p.price);}
 }
 if(items.length<=1000){visit(0,{},0);}else{
  // Bound intermediate search for the full catalog; every retained build still
  // passes the same compatibility and budget rules.
  let frontier=[{parts:{},cost:0}];
  for(let i=0;i<categories.length;i++){
   const candidates=[];
   for(const state of frontier)for(const part of pools[i]){
    const cost=state.cost+part.price;if(cost+minimumRemaining[i+1]+Number(settings.assembly||0)>cap)break;
    const parts={...state.parts,[categories[i]]:part};if(partialCompatible(parts,i))candidates.push({parts,cost});
   }
   const score=state=>{const {cpu,gpu,ram,ssd}=state.parts;return (cpu?.benchmark?.normalizedScore??cpu?.score??0)+(gpu?.benchmark?.normalizedScore??gpu?.score??0)+(ram?.capacity??0)*.05+(ssd?.capacity??0)*.0005;};
   candidates.sort((a,b)=>score(b)-score(a)||a.cost-b.cost);
   const diverse=new Map();for(const state of candidates){const key=JSON.stringify([state.parts.cpu?.id,state.parts.gpu?.id,state.parts.board?.socket,state.parts.ram?.capacity,state.parts.ssd?.capacity]);if(!diverse.has(key))diverse.set(key,state);}
   const chips=new Map();for(const state of [...candidates].sort((a,b)=>a.cost-b.cost)){const key=JSON.stringify([state.parts.cpu?.benchmark?.normalizedScore??state.parts.cpu?.score,state.parts.gpu?.benchmark?.normalizedScore??state.parts.gpu?.score]);if(!chips.has(key))chips.set(key,state);}
   const cheapest=[...candidates].sort((a,b)=>a.cost-b.cost).slice(0,24);
   const x3d=req.profile==='gaming'?[...candidates].filter(c=>isAmdX3d(c.parts.cpu)).sort((a,b)=>score(b)-score(a)||a.cost-b.cost).slice(0,48):[];
   const popular=[...candidates].sort((a,b)=>compareBuildPopularity(a,b)||a.cost-b.cost).slice(0,96);
   frontier=[...new Set([...x3d,...popular,...cheapest,...[...chips.values()].slice(0,192),...[...diverse.values()].slice(0,72)])];
   if(!frontier.length)break;
  }
  combos=frontier.map(state=>assembleBuild(state.parts,req,settings)).filter(Boolean);
 }
 return selectProposals(combos,req,{bounded:items.length>1000,method:items.length>1000?'bounded-search':'enumeration',guarantee:'validated-candidates-only',catalogCount:items.length});
}
export const planNames=['최적 균형안','성능 강화안','절약안'];
export function explain(plan,req,index){
 if(!plan)return '현재 카탈로그와 예산 조건에서는 유효한 구성을 찾지 못했습니다. 예산이나 조건을 조정해 주세요.';
 const p=plan.parts;
 const primary=req.profile==='ai'?`${p.gpu.vram}GB VRAM을 확보해 로컬 AI 용도를 우선했습니다.`:req.profile==='office'?'내장 그래픽으로 별도 GPU 비용을 줄이고 사무 작업에 집중했습니다.':req.profile==='editing'?`${p.ram.capacity}GB 메모리와 ${p.ssd.capacity/1000}TB SSD로 편집 작업 공간을 확보했습니다.`:`${p.cpu.name}와 ${p.gpu.name} 조합입니다.`;
 return primary+' '+(index===2?`균형안보다 비용 부담을 낮추는 선택지입니다.`:index===1?(plan.upgrades?.length?`균형안에서 ${plan.upgrades.join(' · ')} 업그레이드했습니다.`:'허용된 예산 안에서 CPU·GPU 성능, 메모리 또는 SSD를 업그레이드했습니다.'):'용도 적합도와 비용을 함께 고려했습니다.');
}
