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
import {modelTokens,modelKey} from './question-answer.mjs';
export const money=n=>new Intl.NumberFormat('ko-KR').format(n)+'원';
const koreanDigits=Object.fromEntries([...'일이삼사오육칠팔구'].map((c,i)=>[c,i+1])),koreanUnits={십:10,백:100,천:1000};
// '1,500' → 1500, '백오십' → 150, '2백' → 200, '1.5백' → 150, '1천5백' → 1500.
function amount(number){
 let total=0,current=null;
 for(const token of number.replaceAll(',','').match(/\d+(?:\.\d+)?|\D/g)){if(koreanUnits[token]){total+=(current??1)*koreanUnits[token];current=null}else current=Number(koreanDigits[token]??token)}
 return total+(current??0);
}
// Digits ("150만원", "2,000,000 won") or Korean numerals mixed with digits ("백오십만원", "2백만원"); Korean numerals only count before 만.
const amounts=text=>[...text.matchAll(/((?:\d[\d,]*(?:\.\d+)?|[일이삼사오육칠팔구십백천])+)\s*(억\s*원?|만\s*원?|원|won|krw)/gi)].filter(m=>/^[만억]/.test(m[2])||/^\d/.test(m[1])).map(m=>({start:m.index,end:m.index+m[0].length,value:Math.round(amount(m[1])*(m[2].startsWith('억')?100000000:m[2].startsWith('만')?10000:1))}));
// "예산 이백 정도", "삼백 내외": a Korean numeral with 백/천 and no unit means 만 원 in a PC budget.
const bareBudget=/(?<![가-힣\d])((?:(?:\d+|[일이삼사오육칠팔구])?[백천])+(?:\d+|[일이삼사오육칠팔구십])*)(?=\s*(?:정도|쯤|내외|언저리|선|으로|로|이하|이내|까지|안쪽|만큼)|\s*$|[\s,.])/g;
// Bare digits: six or more are won ("예산 1500000"); 30~2000 mean 만 원 when the budget context is clear ("예산 200",
// "배그컴 170" at the end, "300 정도요", "150에서 200 사이", "예산만 200으로"). Resolutions and part sizes ("램 32로") are not budgets.
const rawWon=/(?<![\d.,a-z])(\d{1,3}(?:,\d{3}){2,}|\d{6,})(?![\d,a-z가-힣])/gi;
const bareDigits=/(?<=예산(?:은|을|만|이|도)?|[\s(])(\d{2,4})(?=\s*(?:정도|쯤|내외|언저리|선(?![가-힣])|으로|로(?![가-힣])|에서|사이|이하|이내|까지|언더|안쪽)|\s*[.!?~]*\s*$)/g;
const budgetWord=/예산\s*(?:은|는|을|만|이|도)?\s*$/,partWord=/(?:램|메모리|ram|ssd|vram|파워|모니터|인치|주사율|hz|cpu|그래픽\s*카드|글카|용량|와트)\s*(?:은|는|을|를|도|만|이)?\s*$/i;
// "모니터 30만원 포함해서 총 200만원" → 170만 원; a peripheral's own amount ("모니터는 따로 30만원") is not the PC budget.
const included=/(?:모니터|키보드|마우스|주변\s*기기)[^,.\d\n]{0,8}$/,includes=/^\s*(?:까지|도)?\s*(?:포함|합쳐|같이)/;
export function explicitBudget(text){
 const found=amounts(text);
 // Find the total independently from explicitly included peripheral amounts.
 const pc=found.filter(f=>!included.test(text.slice(0,f.start)));
 if(pc.length){const sum=pc.at(-1).value;const extras=found.reduce((n,f)=>{const peripheral=text.slice(0,f.start).match(included);return n+(peripheral&&!/따로|별도/.test(peripheral[0])&&includes.test(text.slice(f.end))?f.value:0)},0);return extras>0&&extras<sum?sum-extras:sum;}
 if(found.length)return found.at(-1).value;
 const bare=[...text.matchAll(bareBudget)].at(-1);if(bare)return amount(bare[1])*10000;
 const raw=[...text.matchAll(rawWon)].at(-1);if(raw)return Number(raw[1].replaceAll(',',''));
 const digits=[...text.matchAll(bareDigits)].filter(m=>{const n=Number(m[1]),before=text.slice(0,m.index);return n>=30&&n<=2000&&m[1]!=='1080'&&m[1]!=='1440'&&(budgetWord.test(before)||!(/[a-z]\s*$/i.test(before)||partWord.test(before)));});
 return digits.length?Number(digits.at(-1)[1])*10000:null;
}
// Relative change in a follow-up ("예산 10만원만 더 올려줘" → +100,000, "30만원 줄여주세요" → -300,000). Only a text whose
// single amount is followed by an up/down verb counts, so "모니터 30만원 빼고 170만원" stays an explicit 170만 원.
export function budgetChange(text){
 const found=amounts(text);if(found.length!==1)return null;const rest=text.slice(found[0].end);
 if(/^(?:만|정도|쯤|가량)?\s*(?:더\s*)?(?:올|늘|추가|높|증액|써도|쓸게)/.test(rest))return found[0].value;
 if(/^(?:만|정도|쯤|가량)?\s*(?:더\s*)?(?:줄|낮|깎|빼|내려|내리|감액|덜)/.test(rest))return -found[0].value;
 return null;
}
// "3D" only as a word: the X3D in a CPU model name (9800X3D) is not 3D work. Gaming beats office ("사무용인데 가끔 배그도 해요" needs a graphics card); 롤 is not 컨트롤·스크롤·롤러.
// Options are judged by their last mention; a refusal later in the same clause turns it off ("화이트 말고 블랙", "윈도우는 빼주세요").
const optionPatterns={white:/화이트|흰색|하얀|흰\s*(?:케이스|컬러|본체)|white/gi,wifi:/와이파이|wi-?fi|무선(?!\s*(?:마우스|키보드|이어폰|헤드셋|헤드폰|충전|패드|컨트롤러))/gi,os:/윈도우|windows|운영\s*체제|OS\s*포함/gi};
// The refusal window ends at a clause joint ("윈도우 넣고 와이파이는 빼줘": the 빼 belongs to 와이파이).
const refusal=/^(?:(?!고\s)[^,.\n]){0,10}?(?:말고|빼|제외|필요\s*없|없어도|없이|안\s*넣|넣지|아니|싫|집에\s*있|(?<!수도 )(?:있는\s*거|있어요|있습니다)|따로)/;
// Last mentioned resolution that is not refused ("4K 말고 QHD로" → QHD); 5K·8K use the 4K floor.
// Owning a monitor defines its resolution; ownership only opts out of purchasable options.
const resolutionRefusal=/^(?:(?!고\s)[^,.\n]){0,10}?(?:말고|빼|제외|필요\s*없|없어도|없이|안\s*넣|넣지|아니|싫)/;
const resolutionPatterns={'4K':/[458]k|uhd|2160/gi,FHD:/fhd|1080|풀\s*hd|full\s*hd/gi,QHD:/qhd|1440/gi};
const resolutionOf=value=>{const found=Object.entries(resolutionPatterns).flatMap(([name,pattern])=>[...value.matchAll(pattern)].filter(m=>!resolutionRefusal.test(value.slice(m.index+m[0].length))).map(m=>[m.index,name])).sort((a,b)=>a[0]-b[0]);return found.at(-1)?.[1]??(detectProfile(value)==='office'?'FHD':null);};
// White is also cancelled by a later "블랙으로 바꿔주세요" ("화이트 앤 블랙 투톤", "블랙 포인트로" keep it).
const black=/(?:블랙|검정\s*색?|검은\s*색|black)\s*(?:으로|로)(?![가-힣]*\s*포인트)/i;
export const optionRequested=(name,text)=>{const last=[...text.matchAll(optionPatterns[name])].at(-1);if(!last)return false;const rest=text.slice(last.index+last[0].length);return !refusal.test(rest)&&!(name==='white'&&black.test(rest));};
export const detectProfile=value=>/편집|프리미어|다빈치|렌더|(?<![a-z0-9])3D|어도비|adobe|premiere|포토샵|photoshop|라이트룸|lightroom|일러스트레이터|illustrator|애프터\s*이펙트|after\s*effects|블렌더|blender|캐드|(?<![a-z])(?:auto)?cad(?![a-z])|스케치업|sketchup|솔리드웍스|solidworks|마야|maya|라이노|rhino|그래스\s*호퍼|grasshopper|레빗|revit|클립\s*스튜디오|clip\s*studio|웹툰|3ds\s*max|시네마\s*4d|c4d|지브러시|zbrush|캡컷|capcut|브이레이|v-?ray|루미온|lumion|키샷|keyshot|후디니|houdini|퓨전\s*360|fusion\s*360|카티아|catia|인벤터|inventor/i.test(value)?'editing':/로컬|딥러닝|머신\s*러닝|LLM|(?<!웹\s?|앱\s?)개발|AI|스테이블\s*디퓨전|stable\s*diffusion|파이토치|pytorch|sdxl|로라\s*학습|lora|comfy\s*ui|컴피\s*ui|ollama|올라마|파인\s*튜닝|fine-?tun|whisper|cuda|쿠다|llama|vllm|허깅\s*페이스|hugging\s*face|텐서\s*플로|tensorflow|케라스|keras|(?<![a-z])(?:rag|yolo|tts)(?![a-z])|강화\s*학습|음성\s*합성|객체\s*인식/i.test(value)?'ai':/게임|게이밍|배그|(?<![컨트스크])롤(?![러백])|gaming/i.test(value)?'gaming':/사무|회계|엑셀|학습|POS|키오스크|kiosk|cctv|녹화|감시|웹\s*개발|앱\s*개발|코딩|프로그래밍|주식|hts|차트/i.test(value)?'office':/인터넷|웹\s*서핑|웹\s*브라우|문서|인강|온라인\s*강의|유튜브|동영상\s*시청|줌\s*(?:수업|회의|강의)|zoom|화상\s*(?:수업|회의|강의)|(?:온라인|원격|비대면)\s*수업/i.test(value)?'office':null;
export function parseRequirement(text,options={}) {
 const statedBudget=explicitBudget(text);
 const requests=text.split(/\n추가 요청:\s*/);
 const profile=requests.map(detectProfile).filter(Boolean).at(-1)??'gaming';
 const resolution=requests.map(resolutionOf).filter(Boolean).at(-1)??'QHD';
 return {text,profile,budget:statedBudget,resolution,models:modelTokens(text),white:optionRequested('white',text),wifi:optionRequested('wifi',text),os:optionRequested('os',text),allowOver:false,...options,...(unlimitedBudgetRequested(text)?{budget:null,allowOver:false}:{}),budgetSource:unlimitedBudgetRequested(text)?'unlimited':options.budget!=null?(statedBudget!==null?'text':'manual'):statedBudget!==null?'text':'unspecified'};
}
// Text the customer stated wins over an LLM reading; the LLM only names a purpose the rules cannot detect and adds follow-up questions (never a budget prompt).
export function mergeInterpretation(text,llm){
 const local=parseRequirement(text);const stated=text.split(/\n추가 요청:\s*/).some(value=>detectProfile(value));
 return {...local,profile:stated?local.profile:llm.profile,questions:(llm.questions||[]).filter(q=>!/예산/.test(q))};
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
 // A named CPU/GPU model (e.g. 5060ti) restricts that category to the model's products.
 for(const i of [0,3]){const keys=(req.models||[]).filter(key=>items.some(p=>p.category===categories[i]&&modelKey(p)===key));if(keys.length)pools[i]=pools[i].filter(p=>keys.includes(modelKey(p)));}
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
