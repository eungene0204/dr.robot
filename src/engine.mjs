import {catalog,categories} from './catalog.mjs';
import {usablePart,benchmarkState} from './data-policy.mjs';
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
 return {text,profile,budget:statedBudget??2000000,resolution,white:/화이트|흰색/.test(text),wifi:/와이파이|무선|wifi/i.test(text),os:/윈도우|windows|OS 포함/i.test(text),allowOver:false,...options};
}
export function validate(parts){
 const {cpu,board,ram,gpu,ssd,psu,case:k,cooler}=parts; const checks=[];
 const add=(label,values,test,detail)=>checks.push({label,ok:values.some(v=>v===null||v===undefined)?null:Boolean(test()),detail});
 if(categories.some(c=>!parts[c]))return [{label:'필수 부품',ok:false,detail:'누락된 부품이 있습니다.'}];
 add('CPU 소켓',[cpu.socket,board.socket],()=>cpu.socket===board.socket,`${cpu.socket??'미확인'} / ${board.socket??'미확인'}`);
 add('BIOS 지원',[board.bios],()=>board.bios.includes(cpu.compatibilityCpuId||cpu.id),board.biosPreparation||'등록된 CPU 지원 목록 기준');
 add('메모리 규격',[ram.ddr,board.ddr,ram.sticks,board.slots,ram.capacity,board.maxRam],()=>ram.ddr===board.ddr&&ram.sticks<=board.slots&&ram.capacity<=board.maxRam,`DDR${ram.ddr??'?'} · ${ram.capacity??'?'}GB · ${ram.sticks??'?'}슬롯`);
 add('보드 장착',[k.forms,board.form],()=>k.forms.includes(board.form),board.form??'미확인');
 add('GPU 길이',gpu.virtual?[]:[gpu.length,k.gpuLength],()=>gpu.virtual||gpu.length<=k.gpuLength,`${gpu.length??'?'}mm / 허용 ${k.gpuLength??'?'}mm`);
 if(gpu.dataMode==='live'&&!gpu.virtual){
  // Reserve the worst possible GPU slot position for the board form factor.
  // Round thickness upward with a conservative 20 mm per reserved slot.
  // Current build model contains one horizontal GPU and no other expansion cards.
  const lastBoardSlot={mATX:4,ITX:1,ATX:7}[board.form];
  const available=Number.isFinite(k.expansionSlots)&&lastBoardSlot?k.expansionSlots-lastBoardSlot+1:null;
  add('GPU 두께',[gpu.thicknessMm,available],()=>Math.ceil(gpu.thicknessMm/20)<=available,`두께 ${gpu.thicknessMm??'?'}mm / 보수적 가용 ${available??'?'}슬롯 · 수평 GPU 1장 기준`);
 }else add('GPU 두께',gpu.virtual?[]:[gpu.thickness,k.gpuThickness],()=>gpu.virtual||gpu.thickness<=k.gpuThickness,'등록된 슬롯 규격 기준');
 if(gpu.dataMode==='live'&&gpu.connector!=='none'){
  const required=gpu.connectorCount;const available=psu.connectorCounts?.[gpu.connector]??(required===1&&psu.connectors?.includes(gpu.connector)?1:null);
  add('보조 전원',[gpu.connector,psu.connectors,required,available],()=>psu.connectors.includes(gpu.connector)&&available>=required,`${gpu.connector??'?'} ${required??'?'}개 / 제공 ${available??'?'}개`);
 }else add('보조 전원',[gpu.connector,gpu.connector==='none'?true:psu.connectors],()=>gpu.connector==='none'||psu.connectors.includes(gpu.connector),gpu.connector??'미확인');
 const watts=Number.isFinite(cpu.watts)&&Number.isFinite(gpu.watts)?cpu.watts+gpu.watts+70:null;
 add('파워 용량',[watts,psu.capacity,gpu.minPsu],()=>psu.capacity>=Math.max(watts*1.3,gpu.minPsu),`CPU/GPU + 기타 70W 가정 × 1.3 / PSU ${psu.capacity??'?'}W`);
 const tiers=[300,350,400,450,500,550,600,650,700,750,800,850,900,1000,1200,1500,1600,2000];
 const need=Number.isFinite(watts)?Math.max(watts*1.3,gpu.minPsu||0):null;const nextTier=need===null?null:tiers.find(w=>w>need);
 add('파워 한 단계 여유',[need,psu.capacity],()=>nextTier!==undefined&&psu.capacity>=nextTier,`계산 기준 ${need===null?'미확인':Math.ceil(need)+'W'} · 다음 정격 ${nextTier??'없음'}W 이상 권장`);
 if(psu.form&&psu.form!=='ATX')add('파워 장착 규격',[psu.form,k.psuForms],()=>k.psuForms.includes(psu.form),`${psu.form} / 케이스 지원 규격 기준`);
 add('쿨러 장착',[cooler.sockets,cpu.socket,cooler.height,k.coolerHeight],()=>cooler.sockets.includes(cpu.socket)&&cooler.height<=k.coolerHeight,`${cooler.height??'?'}mm / 허용 ${k.coolerHeight??'?'}mm`);
 add('쿨링 용량',[cooler.coolingWatts,cpu.watts],()=>cooler.coolingWatts>=cpu.watts*1.3,'제조사 쿨링 사양 확인 필요 (TDP는 제조사별 비교 한계 있음)');
 add('M.2 슬롯',[ssd.m2,board.m2],()=>ssd.m2<=board.m2,`${ssd.m2??'?'}개 / ${board.m2??'?'}개`);
 add('영상 출력',[gpu.virtual||gpu.id==='g0'?cpu.igpu:true],()=>!(gpu.virtual||gpu.id==='g0')||cpu.igpu,'외장 GPU 또는 내장 그래픽 필요');
 return checks;
}
export function validateBuild(parts,req){
 const checks=validate(parts);if(checks.some(c=>c.label==='필수 부품'))return checks;
 const add=(label,ok,detail)=>checks.push({label,ok:Boolean(ok),detail});
 add('케이스 선호',!req.white||parts.case.color==='white','고객이 지정한 필수 색상');
 add('무선 네트워크',!req.wifi||parts.board.wifi,'Wi-Fi 필수 조건');
 add('운영체제',!req.os||parts.os.id==='o1','정품 OS 포함 조건');
 add('용도 최소 조건',req.profile==='office'||(parts.gpu.id!=='g0'&&parts.ram.capacity>=32),'게임·편집·AI: 외장 GPU와 32GB 이상');
 add('AI VRAM',req.profile!=='ai'||parts.gpu.vram>=16,'로컬 AI: VRAM 16GB 이상');
 add('편집 저장 공간',req.profile!=='editing'||parts.ssd.capacity>=2000,'영상 편집: SSD 2TB 이상');
 return checks;
}
export const total=(parts,settings={})=>Object.values(parts).reduce((s,p)=>s+p.price,0)+Number(settings.assembly||0);
export function performance(parts,req){
 if(parts.cpu?.dataMode==='live'){
  const cpu=parts.cpu.benchmark,gpu=parts.gpu.benchmark;
  if(benchmarkState(parts.cpu)!=='measured'||!Number.isFinite(cpu?.normalizedScore))return null;
  if(req.profile==='office'||parts.gpu.virtual)return Math.round(cpu.normalizedScore*10)/10;
  if(benchmarkState(parts.gpu)!=='measured'||!Number.isFinite(gpu?.normalizedScore)||cpu.version!==gpu.version)return null;
  const cpuWeight=req.profile==='editing'?.6:.25;
  return Math.round((cpu.normalizedScore*cpuWeight+gpu.normalizedScore*(1-cpuWeight))*10)/10;
 }
 return Math.round(req.profile==='office'?parts.cpu.score: req.profile==='editing'?parts.cpu.score*.6+parts.gpu.score*.4:req.profile==='ai'?parts.gpu.vram*5+parts.ram.capacity*.3:parts.cpu.score*.25+parts.gpu.score*.75);
}
// Every proposed build is validated as a complete assembly before it can be shown.
export function assembleBuild(parts,req,settings={}){
 const checks=validateBuild(parts,req);
 if(!checks.every(check=>check.ok===true))return null;
 return {parts:{...parts},total:total(parts,settings),checks,performance:performance(parts,req),dataMode:parts.cpu.dataMode||'demo'};
}
export function recommend(req,settings={},items=catalog){
 if(!Number.isFinite(req.budget)||req.budget<200000||req.budget>20000000)throw new Error('예산은 20만~2,000만 원 사이로 입력해 주세요.');
 const pools=categories.map(c=>items.filter(p=>p.category===c&&usablePart(p)&&!settings.excludedBrands?.includes(p.brand)));
 pools[0]=pools[0].filter(p=>req.profile!=='office'||p.igpu);
 pools[2]=pools[2].filter(p=>p.capacity>=(req.profile==='office'?16:32));
 pools[3]=pools[3].filter(p=>req.profile==='office'?p.id==='g0':p.id!=='g0'&&(req.profile!=='ai'||p.vram>=16));
 pools[4]=pools[4].filter(p=>!/외장|external|USB|케이스|인클로저/i.test(p.name)&&(req.profile!=='editing'||p.capacity>=2000));
 pools[6]=pools[6].filter(p=>!req.white||p.color==='white');
 pools[1]=pools[1].filter(p=>!req.wifi||p.wifi);
 pools[8]=pools[8].filter(p=>req.os?!p.virtual&&p.included!==false:p.id==='o0');
 // Collapse equivalent candidates by fields used by this recommendation model, never by price rank.
 const fields={cpu:['compatibilityCpuId','socket','watts','igpu','score','benchmark'],board:['socket','ddr','form','slots','maxRam','m2','wifi','bios'],ram:['ddr','capacity','sticks'],gpu:['virtual','watts','vram','length','thickness','thicknessMm','connector','connectorCount','minPsu','score','benchmark'],ssd:['capacity','m2','readMBs','writeMBs'],psu:['capacity','connectors','connectorCounts','form'],case:['forms','gpuLength','gpuThickness','expansionSlots','coolerHeight','color','psuForms'],cooler:['sockets','height','coolingWatts','color'],os:['id']};
 for(let i=0;i<pools.length;i++){
  const unique=new Map();for(const part of pools[i].sort((a,b)=>a.price-b.price)){const key=JSON.stringify([...(categories[i]==='cpu'?[part.compatibilityCpuId||part.id]:[]),...fields[categories[i]].map(k=>k==='benchmark'?{version:part.benchmark?.version,normalizedScore:part.benchmark?.normalizedScore}:part[k])]);if(!unique.has(key))unique.set(key,part);}
  pools[i]=[...unique.values()];
 }
 // A higher-priced PSU with no capacity/connector advantage cannot improve this model.
 const psuKey=p=>JSON.stringify([p.form||'ATX',[...(p.connectors||[])].sort(),p.connectorCounts||null]);
 pools[5]=pools[5].filter(part=>!pools[5].some(other=>other!==part&&psuKey(other)===psuKey(part)&&other.price<=part.price&&other.capacity>=part.capacity&&(other.price<part.price||other.capacity>part.capacity)));
 // Keep board-specific GPU dimensions, but discard strictly dominated variants of the same measured chip.
 const gpuKey=p=>JSON.stringify([Boolean(p.virtual),p.benchmark?.version,p.benchmark?.normalizedScore,p.score,p.vram,p.connector,p.connectorCount]);
 const gpuMetrics=['watts','length','thicknessMm','minPsu'];
 pools[3]=pools[3].filter(part=>!pools[3].some(other=>other!==part&&gpuKey(other)===gpuKey(part)&&other.price<=part.price&&gpuMetrics.every(k=>Number.isFinite(part[k])&&Number.isFinite(other[k])&&other[k]<=part[k])&&(other.price<part.price||gpuMetrics.some(k=>other[k]<part[k]))));
 // Storage with a higher price and no capacity or speed advantage cannot
 // improve any plan. Keep every price/specification tradeoff in the search.
 pools[4]=pools[4].filter(part=>!pools[4].some(other=>other!==part&&other.m2===part.m2&&other.price<=part.price&&other.capacity>=part.capacity&&['readMBs','writeMBs'].every(k=>!Number.isFinite(part[k])||(Number.isFinite(other[k])&&other[k]>=part[k]))&&(other.price<part.price||other.capacity>part.capacity||['readMBs','writeMBs'].some(k=>Number.isFinite(other[k])&&other[k]>(part[k]??0)))));
 const depends={'CPU 소켓':['cpu','board'],'BIOS 지원':['cpu','board'],'메모리 규격':['board','ram'],'보드 장착':['board','case'],'GPU 길이':['gpu','case'],'GPU 두께':['gpu','board','case'],'파워 장착 규격':['psu','case'],'보조 전원':['gpu','psu'],'파워 용량':['cpu','gpu','psu'],'쿨러 장착':['cooler','cpu','case'],'쿨링 용량':['cooler','cpu'],'M.2 슬롯':['ssd','board'],'영상 출력':['gpu','cpu']};
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
 const cap=Math.floor(req.budget*(req.allowOver?1.1:1));
 let combos=[];
 const leastCost=new Map();
 function visit(i,parts,cost){
  // Keep storage capacity and speed distinct when pruning equivalent builds.
  // After the PSU check its identity cannot affect future compatibility tests.
  if(i>=6){const key=JSON.stringify([i,parts.cpu.id,i<7?parts.board.id:null,parts.gpu.id,parts.ram.capacity,parts.ssd.capacity,parts.ssd.readMBs,parts.ssd.writeMBs,i===7?parts.case.id:null,i===6?(parts.psu.form||'ATX'):null]);const prior=leastCost.get(key);if(prior!==undefined&&prior<=cost)return;leastCost.set(key,cost);}
  if(++visited>500000)throw new Error('후보 조합이 너무 많습니다. 카탈로그나 필수 조건으로 후보를 줄여 주세요.');
  if(cost+minimumRemaining[i]+Number(settings.assembly||0)>cap)return;
  if(i===categories.length){const build=assembleBuild(parts,req,settings);if(build)combos.push(build);return;}
  for(const p of pools[i]){if(cost+p.price+minimumRemaining[i+1]+Number(settings.assembly||0)>cap)break;const next={...parts,[categories[i]]:p};if(partialCompatible(next,i))visit(i+1,next,cost+p.price);}
 }
 visit(0,{},0);
 const used=new Set();
 // Compare known CPU/GPU performance separately so capacity alone never masks a downgrade.
 const chipScore=p=>p.dataMode==='live'?p.benchmark?.normalizedScore:p.score;
 const noChipDowngrade=(next,base)=>next.id===base.id||(Number.isFinite(chipScore(next))&&Number.isFinite(chipScore(base))&&chipScore(next)>=chipScore(base));
 const upgrades=(next,base)=>{
  if(!base)return [];
  const n=next.parts,b=base.parts;
  const speedKeys=['readMBs','writeMBs'];
  const storageSlower=speedKeys.some(k=>Number.isFinite(b.ssd[k])&&(!Number.isFinite(n.ssd[k])||n.ssd[k]<b.ssd[k]));
  if(storageSlower)return [];
  if(!noChipDowngrade(n.cpu,b.cpu)||!noChipDowngrade(n.gpu,b.gpu)||n.ram.capacity<b.ram.capacity||n.ssd.capacity<b.ssd.capacity)return [];
  const changes=[];
  if(n.cpu.id!==b.cpu.id&&chipScore(n.cpu)>chipScore(b.cpu))changes.push(`CPU: ${b.cpu.name} → ${n.cpu.name}`);
  if(n.gpu.id!==b.gpu.id&&chipScore(n.gpu)>chipScore(b.gpu))changes.push(`GPU: ${b.gpu.name} → ${n.gpu.name}`);
  if(n.ram.capacity>b.ram.capacity)changes.push(`메모리: ${b.ram.capacity}GB → ${n.ram.capacity}GB`);
  if(n.ssd.capacity>b.ssd.capacity)changes.push(`SSD 용량: ${b.ssd.capacity}GB → ${n.ssd.capacity}GB`);
  for(const [key,label] of [['readMBs','순차 읽기'],['writeMBs','순차 쓰기']])if(Number.isFinite(b.ssd[key])&&Number.isFinite(n.ssd[key])&&n.ssd[key]>b.ssd[key])changes.push(`SSD ${label} 사양: ${b.ssd[key]} → ${n.ssd[key]}MB/s`);
  return changes;
 };
 const pick=(mode,min,max)=>{
  let options=combos.filter(c=>c.total>=min&&c.total<=max&&(mode!=='enhanced'||(balanced&&upgrades(c,balanced).length>0))&&!used.has(categories.map(k=>c.parts[k].id).join('|')));
  if(mode==='balanced'){
   const measured=options.filter(c=>Number.isFinite(c.performance));
   if(measured.length){const peak=measured.reduce((max,c)=>Math.max(max,c.performance),0);options=measured.filter(c=>c.performance>=peak*.95);}
  }
  options.sort((a,b)=>{
   if(mode==='balanced')return a.total-b.total||(b.performance??0)-(a.performance??0);
   const score=c=>mode==='saving'?(c.performance??0)/(c.total/1000000):(c.performance??0);
   return score(b)-score(a)||(mode==='enhanced'?(b.parts.ram.capacity-a.parts.ram.capacity||b.parts.ssd.capacity-a.parts.ssd.capacity||(b.parts.ssd.readMBs??0)-(a.parts.ssd.readMBs??0)||(b.parts.ssd.writeMBs??0)-(a.parts.ssd.writeMBs??0)):0)||a.total-b.total;
  });
  const best=options[0];if(!best)return null;
  used.add(categories.map(k=>best.parts[k].id).join('|'));
  return {...best,id:mode,checks:best.checks,targetMet:true,...(mode==='enhanced'?{upgrades:upgrades(best,balanced)}:{})};
 };
 // Preserve near-peak performance while avoiding spending merely to fill the budget.
 const balanced=pick('balanced',0,req.budget);
 const enhanced=pick('enhanced',0,cap);
 const savingCap=Math.min(req.budget*.9,balanced?balanced.total-1:req.budget*.9);
 const saving=pick('saving',0,savingCap);
 return [balanced,enhanced,saving].map((x,i)=>x?{...x,id:['balanced','enhanced','saving'][i],targetMet:i===0?true:i===2?x.total>=req.budget*.8&&x.total<=req.budget*.9:true}:null);
}
export const planNames=['최적 균형안','성능 강화안','절약안'];
export function explain(plan,req,index){
 if(!plan)return '현재 카탈로그와 예산 조건에서는 유효한 구성을 찾지 못했습니다. 예산이나 조건을 조정해 주세요.';
 const p=plan.parts;
 const primary=req.profile==='ai'?`${p.gpu.vram}GB VRAM을 확보해 로컬 AI 용도를 우선했습니다.`:req.profile==='office'?'내장 그래픽으로 별도 GPU 비용을 줄이고 사무 작업에 집중했습니다.':req.profile==='editing'?`${p.ram.capacity}GB 메모리와 ${p.ssd.capacity/1000}TB SSD로 편집 작업 공간을 확보했습니다.`:`${p.cpu.name}와 ${p.gpu.name} 조합입니다.`;
 return primary+' '+(index===2?`균형안보다 비용 부담을 낮추는 선택지입니다.`:index===1?(plan.upgrades?.length?`균형안에서 ${plan.upgrades.join(' · ')} 업그레이드했습니다.`:'허용된 예산 안에서 CPU·GPU 성능, 메모리 또는 SSD를 업그레이드했습니다.'):'용도 적합도와 비용을 함께 고려했습니다.');
}
