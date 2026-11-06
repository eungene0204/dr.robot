import {isAmdX3d} from './gaming-cpu-policy.mjs';
import {compareBuildPopularity,popularitySummary} from './popularity.mjs';
import {budgetLimit,hasBudget} from './budget-policy.mjs';
import {categories} from './catalog.mjs';
export const proposalObjectives={balanced:'높은 성능 구간에서 비용 최소화',enhanced:'주요 사양을 낮추지 않는 개선안 중 성능 최대화',saving:'균형안보다 저렴하고 예산 90% 이하에서 성능/가격 최대화'};
export function selectProposals(combos,req,{bounded=false,...search}={}){
 const cap=Math.floor(budgetLimit(req));
 const used=new Set();
 // Compare known CPU/GPU performance separately so capacity alone never masks a downgrade.
 const chipScore=p=>p.dataMode==='live'?p.benchmark?.normalizedScore:p.score;
 const x3dPreference=(next,base)=>req.profile==='gaming'&&req.performanceMode!=='measured'&&!isAmdX3d(base.parts.cpu)&&isAmdX3d(next.parts.cpu);
 const noChipDowngrade=(next,base)=>next.id===base.id||(Number.isFinite(chipScore(next))&&Number.isFinite(chipScore(base))&&chipScore(next)>=chipScore(base));
 const upgrades=(next,base)=>{
  if(!base)return [];
  const n=next.parts,b=base.parts;
  if(req.profile==='gaming'){
   const changed=n.cpu.id!==b.cpu.id||n.gpu.id!==b.gpu.id;
   const improved=req.performanceMode==='measured'?changed&&next.performance>base.performance:
    x3dPreference(next,base)||(n.cpu.id!==b.cpu.id&&chipScore(n.cpu)>chipScore(b.cpu))||(n.gpu.id!==b.gpu.id&&chipScore(n.gpu)>chipScore(b.gpu));
   if(!improved)return [];
  }
  const speedKeys=['readMBs','writeMBs'];
  const storageSlower=speedKeys.some(k=>Number.isFinite(b.ssd[k])&&(!Number.isFinite(n.ssd[k])||n.ssd[k]<b.ssd[k]));
  if(storageSlower)return [];
  if(n.ram.capacity<b.ram.capacity||n.ssd.capacity<b.ssd.capacity)return [];
  if(req.performanceMode==='measured'){if(next.performance<base.performance||n.gpu.vram<b.gpu.vram)return [];}else if((!x3dPreference(next,base)&&!noChipDowngrade(n.cpu,b.cpu))||!noChipDowngrade(n.gpu,b.gpu))return [];
  const changes=[];
  if(x3dPreference(next,base))changes.push(`CPU: ${b.cpu.name} → ${n.cpu.name} (게임용 X3D 선호 적용 · FPS 실측 아님)`);
  if(req.performanceMode==='measured'&&next.performance>base.performance)changes.push(`${req.workload} 실측: ${base.performanceBasis.measurement.value} → ${next.performanceBasis.measurement.value} ${next.performanceBasis.measurement.unit}`);
  if(!x3dPreference(next,base)&&req.performanceMode!=='measured'&&n.cpu.id!==b.cpu.id&&chipScore(n.cpu)>chipScore(b.cpu))changes.push(`CPU: ${b.cpu.name} → ${n.cpu.name}`);
  if(req.performanceMode!=='measured'&&n.gpu.id!==b.gpu.id&&chipScore(n.gpu)>chipScore(b.gpu))changes.push(`GPU: ${b.gpu.name} → ${n.gpu.name}`);
  if(n.ram.capacity>b.ram.capacity)changes.push(`메모리: ${b.ram.capacity}GB → ${n.ram.capacity}GB`);
  if(n.ssd.capacity>b.ssd.capacity)changes.push(`SSD 용량: ${b.ssd.capacity}GB → ${n.ssd.capacity}GB`);
  for(const [key,label] of [['readMBs','순차 읽기'],['writeMBs','순차 쓰기']])if(Number.isFinite(b.ssd[key])&&Number.isFinite(n.ssd[key])&&n.ssd[key]>b.ssd[key])changes.push(`SSD ${label} 사양: ${b.ssd[key]} → ${n.ssd[key]}MB/s`);
  return changes;
 };
 const pick=(mode,min,max)=>{
  let options=combos.filter(c=>c.total>=min&&c.total<=max&&(mode!=='enhanced'||(balanced&&(hasBudget(req)||c.performance>balanced.performance||x3dPreference(c,balanced))&&upgrades(c,balanced).length>0))&&!used.has(categories.map(k=>c.parts[k].id).join('|')));
  if(mode==='balanced'&&hasBudget(req)){
   const measured=options.filter(c=>Number.isFinite(c.performance));
   if(measured.length){const peak=measured.reduce((max,c)=>Math.max(max,c.performance),0);options=measured.filter(c=>c.performance>=peak*.95);}
  }
  options.sort((a,b)=>{
   if(mode==='enhanced'&&req.profile==='gaming'){const preference=Number(isAmdX3d(b.parts.cpu))-Number(isAmdX3d(a.parts.cpu));if(preference)return preference;}
   const popularity=compareBuildPopularity(a,b);
   if(mode==='balanced'&&!hasBudget(req)&&req.profile==='gaming'&&req.resolution==='4K'&&req.performanceMode!=='measured'){return (chipScore(b.parts.gpu)??0)-(chipScore(a.parts.gpu)??0)||(chipScore(b.parts.cpu)??0)-(chipScore(a.parts.cpu)??0)||popularity||a.total-b.total;}
   if(mode==='balanced')return hasBudget(req)?popularity||a.total-b.total||(b.performance??0)-(a.performance??0):(b.performance??0)-(a.performance??0)||popularity||a.total-b.total;
   const score=c=>mode==='saving'?(c.performance??0)/(c.total/1000000):(c.performance??0);
   return score(b)-score(a)||popularity||(mode==='enhanced'?(b.parts.ram.capacity-a.parts.ram.capacity||b.parts.ssd.capacity-a.parts.ssd.capacity||(b.parts.ssd.readMBs??0)-(a.parts.ssd.readMBs??0)||(b.parts.ssd.writeMBs??0)-(a.parts.ssd.writeMBs??0)):0)||a.total-b.total;
  });
  const best=options[0];if(!best)return null;
  used.add(categories.map(k=>best.parts[k].id).join('|'));
  return {...best,id:mode,checks:best.checks,targetMet:true,...(mode==='enhanced'?{upgrades:upgrades(best,balanced)}:{})};
 };
 // Preserve near-peak performance while avoiding spending merely to fill the budget.
 let balanced=pick('balanced',0,budgetLimit(req,'balanced'));
 let enhanced=pick('enhanced',0,cap);
 let jointlySelected=false;
 if(req.profile==='gaming'&&hasBudget(req)&&balanced&&!enhanced){
  const original=balanced;const signature=p=>categories.map(k=>p.parts[k].id).join('|');
  const bases=combos.filter(c=>c.total<=req.budget&&Number.isFinite(c.performance)).sort((a,b)=>b.performance-a.performance||compareBuildPopularity(a,b)||a.total-b.total);
  for(const base of bases){
   if(!combos.some(c=>c.total<=cap&&(c.performance>base.performance||x3dPreference(c,base))&&signature(c)!==signature(base)&&upgrades(c,base).length))continue;
   used.delete(signature(original));balanced={...base,id:'balanced',targetMet:true};used.add(signature(base));
   enhanced=pick('enhanced',0,cap);
   if(enhanced){jointlySelected=true;break;}
   used.delete(signature(base));balanced=original;used.add(signature(original));
  }
 }
 const savingCap=hasBudget(req)?Math.min(req.budget*.9,balanced?balanced.total-1:req.budget*.9):(balanced?balanced.total*.9:Infinity);
 const saving=pick('saving',0,savingCap);
 return [balanced,enhanced,saving].map((x,i)=>x?{...x,selection:{...search,jointlySelected,popularity:popularitySummary(x.parts),gamingCpuPreference:req.profile==='gaming'?'amd-x3d-if-valid':'none',rankingPolicy:'performance-first-popularity-within-tier',performanceRetention:jointlySelected?null:hasBudget(req)?.95:1,budgetMode:hasBudget(req)?'limited':'unlimited',objective:popularitySummary(x.parts).known>0?(i===0?'성능 상위 구간 내 인기·가격 비교':i===1?'CPU·GPU 등 용도 성능 향상 우선, 동급은 인기·가격 비교':'성능 대비 가격 우선, 동급은 인기 비교'):!hasBudget(req)&&i===0?(req.profile==='gaming'&&req.resolution==='4K'&&req.performanceMode!=='measured'?'4K 게임: GPU 지수 우선, CPU 지수 다음, 동일 성능 비용 최소화':'예산 상한 없이 성능 최대화 후 비용 최소화'):proposalObjectives[['balanced','enhanced','saving'][i]],performanceKind:x.performanceBasis?.kind||'unknown',candidateCount:combos.length},id:['balanced','enhanced','saving'][i],targetMet:i===0?true:i===2&&hasBudget(req)?x.total>=req.budget*.8&&x.total<=req.budget*.9:true}:null);
}