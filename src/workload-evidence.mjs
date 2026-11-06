import {benchmarkState,isFresh} from './data-policy.mjs';
import {categories} from './catalog.mjs';
export const performancePolicies={
 gaming:{cpuWeight:.25,label:'Blender 대체 지수',limitation:'게임별 FPS·해상도별 병목을 직접 측정한 결과가 아닙니다.'},
 editing:{cpuWeight:.6,label:'Blender 렌더 대체 지수',limitation:'Premiere·DaVinci 등 개별 편집 프로그램의 실측 결과가 아닙니다.'},
 ai:{cpuWeight:.25,label:'Blender 대체 지수',limitation:'AI 모델별 토큰 처리량·실행 가능 여부를 보장하지 않습니다.'},
 office:{cpuWeight:1,label:'Blender CPU 대체 지수',limitation:'사무 프로그램의 응답성을 직접 측정한 결과가 아닙니다.'},
};
export function measurementIssue(m){
 if(!m||!['gaming','editing','ai','office'].includes(m.profile)||typeof m.workload!=='string'||!m.workload.trim())return '용도·작업 이름이 필요합니다.';
 if(!m.configuration||!categories.every(c=>typeof m.configuration[c]==='string'&&m.configuration[c]))return '전체 측정 구성이 필요합니다.';
 if(!m.sourceUrl||!/^https:\/\//.test(m.sourceUrl)||!Number.isFinite(Date.parse(m.observedAt)))return 'HTTPS 출처와 관측 시각이 필요합니다.';
 if(!m.softwareVersion||!m.settings||typeof m.settings!=='object'||Array.isArray(m.settings))return '소프트웨어 버전과 측정 설정이 필요합니다.';
 if(m.profile==='gaming'&&!['FHD','QHD','4K'].includes(m.resolution))return '게임 측정에는 해상도가 필요합니다.';
 if(!['fps','tokens/s','seconds','score'].includes(m.unit)||!['higher','lower'].includes(m.direction)||!Number.isFinite(m.value)||m.value<=0)return '양수 측정값·단위·성능 방향이 필요합니다.';
 if(m.unit==='seconds'&&m.direction!=='lower'||['fps','tokens/s'].includes(m.unit)&&m.direction!=='higher')return '측정 단위와 성능 방향이 맞지 않습니다.';
 return null;
}
export function matchMeasurement(parts,req,now=Date.now()){
 // Exact build, workload and measurement settings only. Never infer a full-build FPS from a GPU score.
 if(!req.workload||!req.measurementContext)return null;
 const context=req.measurementContext;
 return (parts.cpu?.workloadMeasurements||[]).filter(m=>m.reviewed===true&&!measurementIssue(m)&&isFresh(m.observedAt,45*24,now)&&m.profile===req.profile&&m.workload===req.workload&&m.softwareVersion===context.softwareVersion&&m.unit===context.unit&&m.direction===context.direction&&JSON.stringify(Object.entries(m.settings).sort())===JSON.stringify(Object.entries(context.settings||{}).sort())&&(req.profile!=='gaming'||m.resolution===req.resolution)&&categories.every(c=>m.configuration[c]===parts[c]?.id)).sort((a,b)=>Date.parse(b.observedAt)-Date.parse(a.observedAt))[0]||null;
}
export function evaluatePerformance(parts,req){
 const policy=performancePolicies[req.profile]||performancePolicies.gaming;
 const measured=matchMeasurement(parts,req);
 if(req.performanceMode==='measured')return measured?{score:measured.direction==='higher'?measured.value:1/measured.value,kind:'measured',label:`${measured.workload} 실측`,measurement:measured,limitation:null}:{score:null,kind:'missing',label:'해당 작업 실측 없음',limitation:'동일 구성·작업·설정의 유효한 실측 자료가 없습니다.'};
 if(parts.cpu?.dataMode!=='live')return {score:Math.round(req.profile==='office'?parts.cpu.score:req.profile==='editing'?parts.cpu.score*.6+parts.gpu.score*.4:req.profile==='ai'?parts.gpu.vram*5+parts.ram.capacity*.3:parts.cpu.score*.25+parts.gpu.score*.75),kind:'demo',label:'시연 지수',limitation:'가상 성능 데이터'};
 const cpu=parts.cpu.benchmark,gpu=parts.gpu.benchmark;
 const cpuOnly=req.profile==='office'||parts.gpu.virtual;
 const available=benchmarkState(parts.cpu)==='measured'&&Number.isFinite(cpu?.normalizedScore)&&(cpuOnly||benchmarkState(parts.gpu)==='measured'&&Number.isFinite(gpu?.normalizedScore)&&cpu.version===gpu.version);
 const score=available?Math.round((cpuOnly?cpu.normalizedScore:cpu.normalizedScore*policy.cpuWeight+gpu.normalizedScore*(1-policy.cpuWeight))*10)/10:null;
 return {score,kind:'proxy',label:policy.label,limitation:policy.limitation,cpuWeight:cpuOnly?1:policy.cpuWeight,sources:[cpu,...(cpuOnly?[]:[gpu])].filter(Boolean).map(b=>({sourceUrl:b.sourceUrl,observedAt:b.observedAt,version:b.version})),availableMeasurement:measured};
}
