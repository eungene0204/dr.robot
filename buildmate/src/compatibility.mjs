import {categories} from './catalog.mjs';
export const compatibilityDependencies={'CPU 소켓':['cpu','board'],'BIOS 지원':['cpu','board'],'메모리 규격':['board','ram'],'보드 장착':['board','case'],'GPU 길이':['gpu','case'],'GPU 두께':['gpu','board','case'],'파워 장착 규격':['psu','case'],'보조 전원':['gpu','psu'],'파워 용량':['cpu','gpu','psu'],'쿨러 장착':['cooler','cpu','case'],'쿨링 용량':['cooler','cpu'],'M.2 슬롯':['ssd','board'],'영상 출력':['gpu','cpu']};
export function validate(parts){
 const {cpu,board,ram,gpu,ssd,psu,case:k,cooler}=parts; const checks=[];
 const add=(label,values,test,detail)=>checks.push({label,ok:values.some(v=>v===null||v===undefined)?null:Boolean(test()),detail});
 if(categories.some(c=>!parts[c]))return [{label:'필수 부품',ok:false,detail:'누락된 부품이 있습니다.'}];
 add('CPU 소켓',[cpu.socket,board.socket],()=>cpu.socket===board.socket,`${cpu.socket??'미확인'} / ${board.socket??'미확인'}`);
 const cpuId=cpu.compatibilityCpuId||cpu.id;
 if(Array.isArray(board.cpuSupport)){
  const records=board.cpuSupport.filter(r=>r.cpuId===cpuId);
  const evaluated=records.map(r=>{if(!r.evidence?.sourceUrl||!r.evidence?.observedAt)return null;if(r.boardRevision&&!board.revision)return null;if(r.boardRevision&&r.boardRevision!==board.revision)return false;if(r.biosVersions?.length&&!board.installedBios)return null;return !r.biosVersions?.length||r.biosVersions.includes(board.installedBios)});
  const ok=evaluated.includes(true)?true:evaluated.includes(null)?null:false;
  checks.push({label:'BIOS 지원',ok,detail:'CPU 지원 목록·보드 리비전·설치 BIOS의 명시된 조건 기준',ruleId:'cpu-support',evidence:records.map(r=>r.evidence).filter(Boolean)});
 }else add('BIOS 지원',[board.bios],()=>board.bios.includes(cpuId),board.biosPreparation||'기존 등록 CPU 지원 목록 기준 · BIOS 버전 조건 별도 미등록');
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
 for(const check of checks){check.ruleId??=check.label;check.status=check.ok===true?'pass':check.ok===false?'fail':'unknown';}
 return checks;
}
