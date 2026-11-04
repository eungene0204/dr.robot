import {catalog,categories} from './catalog.mjs';
import {usablePart,benchmarkState} from './data-policy.mjs';
export const money=n=>new Intl.NumberFormat('ko-KR').format(n)+'원';
export function parseRequirement(text,options={}) {
 const won=text.match(/(\d+(?:\.\d+)?)\s*만\s*원?/); const raw=text.match(/(\d[\d,]{4,})\s*원/);
 let profile=/편집|프리미어|다빈치|렌더|3D/i.test(text)?'editing':/로컬|딥러닝|LLM|개발|AI/i.test(text)?'ai':/사무|엑셀|학습|POS/i.test(text)?'office':'gaming';
 return {text,profile,budget:won?Math.round(Number(won[1])*10000):raw?Number(raw[1].replaceAll(',','')):2000000,resolution:/4k/i.test(text)?'4K':/FHD|1080/i.test(text)?'FHD':'QHD',white:/화이트|흰색/.test(text),wifi:/와이파이|무선|wifi/i.test(text),os:/윈도우|windows|OS 포함/i.test(text),allowOver:false,...options};
}
export function validate(parts){
 const {cpu,board,ram,gpu,ssd,psu,case:k,cooler}=parts; const checks=[];
 const add=(label,values,test,detail)=>checks.push({label,ok:values.some(v=>v===null||v===undefined)?null:Boolean(test()),detail});
 if(categories.some(c=>!parts[c]))return [{label:'필수 부품',ok:false,detail:'누락된 부품이 있습니다.'}];
 add('CPU 소켓',[cpu.socket,board.socket],()=>cpu.socket===board.socket,`${cpu.socket??'미확인'} / ${board.socket??'미확인'}`);
 add('BIOS 지원',[board.bios],()=>board.bios.includes(cpu.id),'제조사 CPU 지원 목록·출고 BIOS 확인 필요');
 add('메모리 규격',[ram.ddr,board.ddr,ram.sticks,board.slots,ram.capacity,board.maxRam],()=>ram.ddr===board.ddr&&ram.sticks<=board.slots&&ram.capacity<=board.maxRam,`DDR${ram.ddr??'?'} · ${ram.capacity??'?'}GB · ${ram.sticks??'?'}슬롯`);
 add('보드 장착',[k.forms,board.form],()=>k.forms.includes(board.form),board.form??'미확인');
 add('GPU 길이',gpu.virtual?[]:[gpu.length,k.gpuLength],()=>gpu.virtual||gpu.length<=k.gpuLength,`${gpu.length??'?'}mm / 허용 ${k.gpuLength??'?'}mm`);
 add('GPU 두께',gpu.virtual?[]:[gpu.thickness,k.gpuThickness],()=>gpu.virtual||gpu.thickness<=k.gpuThickness,'두께·장착 위치·확장카드 간섭 확인 필요');
 add('보조 전원',[gpu.connector,gpu.connector==='none'?true:psu.connectors],()=>gpu.connector==='none'||psu.connectors.includes(gpu.connector),gpu.connector??'미확인');
 const watts=Number.isFinite(cpu.watts)&&Number.isFinite(gpu.watts)?cpu.watts+gpu.watts+70:null;
 add('파워 용량',[watts,psu.capacity,gpu.minPsu],()=>psu.capacity>=Math.max(watts*1.3,gpu.minPsu),`CPU/GPU + 기타 70W 가정 × 1.3 / PSU ${psu.capacity??'?'}W`);
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
export function recommend(req,settings={},items=catalog){
 if(!Number.isFinite(req.budget)||req.budget<200000||req.budget>20000000)throw new Error('예산은 20만~2,000만 원 사이로 입력해 주세요.');
 const pools=categories.map(c=>items.filter(p=>p.category===c&&usablePart(p)&&!settings.excludedBrands?.includes(p.brand)));
 pools[0]=pools[0].filter(p=>req.profile!=='office'||p.igpu);
 pools[2]=pools[2].filter(p=>p.capacity>=(req.profile==='office'?16:32));
 pools[3]=pools[3].filter(p=>req.profile==='office'?p.id==='g0':p.id!=='g0'&&(req.profile!=='ai'||p.vram>=16));
 pools[4]=pools[4].filter(p=>req.profile!=='editing'||p.capacity>=2000);
 pools[6]=pools[6].filter(p=>!req.white||p.color==='white');
 pools[1]=pools[1].filter(p=>!req.wifi||p.wifi);
 pools[8]=pools[8].filter(p=>req.os?!p.virtual&&p.included!==false:p.id==='o0');
 for(let i=0;i<pools.length;i++)pools[i]=pools[i].sort((a,b)=>a.price-b.price).slice(0,12);
 let visited=0;
 const cap=Math.floor(req.budget*(req.allowOver?1.1:1));
 let combos=[];
 function visit(i,parts,cost){
  if(++visited>500000)throw new Error('후보 조합이 너무 많습니다. 카탈로그나 필수 조건으로 후보를 줄여 주세요.');
  if(cost+Number(settings.assembly||0)>cap)return;
  if(i===categories.length){if(validateBuild(parts,req).every(x=>x.ok!==false))combos.push({parts:{...parts},total:total(parts,settings),performance:performance(parts,req),dataMode:parts.cpu.dataMode||'demo'});return;}
  for(const p of pools[i])visit(i+1,{...parts,[categories[i]]:p},cost+p.price);
 }
 visit(0,{},0);
 const used=new Set();
 // Compare known CPU/GPU performance separately so capacity alone never masks a downgrade.
 const chipScore=p=>p.dataMode==='live'?p.benchmark?.normalizedScore:p.score;
 const noChipDowngrade=(next,base)=>next.id===base.id||(Number.isFinite(chipScore(next))&&Number.isFinite(chipScore(base))&&chipScore(next)>=chipScore(base));
 const upgrades=(next,base)=>{
  if(!base)return [];
  const n=next.parts,b=base.parts;
  if(!noChipDowngrade(n.cpu,b.cpu)||!noChipDowngrade(n.gpu,b.gpu)||n.ram.capacity<b.ram.capacity||n.ssd.capacity<b.ssd.capacity)return [];
  const changes=[];
  if(n.cpu.id!==b.cpu.id&&chipScore(n.cpu)>chipScore(b.cpu))changes.push(`CPU: ${b.cpu.name} → ${n.cpu.name}`);
  if(n.gpu.id!==b.gpu.id&&chipScore(n.gpu)>chipScore(b.gpu))changes.push(`GPU: ${b.gpu.name} → ${n.gpu.name}`);
  if(n.ram.capacity>b.ram.capacity)changes.push(`메모리: ${b.ram.capacity}GB → ${n.ram.capacity}GB`);
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
   return score(b)-score(a)||a.total-b.total;
  });
  const best=options[0];if(!best)return null;
  used.add(categories.map(k=>best.parts[k].id).join('|'));
  return {...best,id:mode,checks:validateBuild(best.parts,req),targetMet:true,...(mode==='enhanced'?{upgrades:upgrades(best,balanced)}:{})};
 };
 // Preserve near-peak performance while avoiding spending merely to fill the budget.
 const balanced=pick('balanced',0,req.budget);
 const enhanced=pick('enhanced',0,cap);
 const saving=pick('saving',req.budget*.8,req.budget*.9)||pick('saving',0,Math.min(req.budget*.9,balanced?.total-1||req.budget*.9));
 return [balanced,enhanced,saving].map((x,i)=>x?{...x,id:['balanced','enhanced','saving'][i],targetMet:i===0?true:i===2?x.total>=req.budget*.8&&x.total<=req.budget*.9:true}:null);
}
export const planNames=['최적 균형안','성능 강화안','절약안'];
export function explain(plan,req,index){
 if(!plan)return '현재 카탈로그와 예산 조건에서는 유효한 구성을 찾지 못했습니다. 예산이나 조건을 조정해 주세요.';
 const p=plan.parts;
 const primary=req.profile==='ai'?`${p.gpu.vram}GB VRAM을 확보해 로컬 AI 용도를 우선했습니다.`:req.profile==='office'?'내장 그래픽으로 별도 GPU 비용을 줄이고 사무 작업에 집중했습니다.':req.profile==='editing'?`${p.ram.capacity}GB 메모리와 ${p.ssd.capacity/1000}TB SSD로 편집 작업 공간을 확보했습니다.`:`${p.cpu.name}와 ${p.gpu.name} 조합입니다.`;
 return primary+' '+(index===2?`균형안보다 비용 부담을 낮추는 선택지입니다.`:index===1?(plan.upgrades?.length?`균형안에서 ${plan.upgrades.join(' · ')} 업그레이드했습니다.`:'허용된 예산 안에서 CPU·GPU 성능 또는 메모리 용량을 높였습니다.'):'용도 적합도와 비용을 함께 고려했습니다.');
}
