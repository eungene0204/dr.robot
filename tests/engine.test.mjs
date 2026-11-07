import test from 'node:test';
import assert from 'node:assert/strict';
import {catalog} from '../src/catalog.mjs';
import {parseRequirement,mergeInterpretation,recommend,assembleBuild,validate,total,explicitBudget,detectProfile} from '../src/engine.mjs';
const settings={assembly:30000};
test('한글 예산과 용도를 구조화한다',()=>{const r=parseRequirement('프리미어 4K 편집, 250만 원, 화이트');assert.equal(r.budget,2500000);assert.equal(r.profile,'editing');assert.equal(r.resolution,'4K');assert.equal(r.white,true)});
test('어도비 등 크리에이티브 도구 요청은 편집 용도로 해석한다',()=>{for(const text of ['200만원 이하 adobe용 견적','포토샵 라이트룸용 150만 원','애프터 이펙트 작업용'])assert.equal(parseRequirement(text).profile,'editing',text)});
test('반환하는 모든 조합은 예산과 호환성 조건을 만족한다',()=>{for(const profile of ['gaming','editing','office','ai'])for(const budget of [600000,1000000,2000000,3000000]){const req=parseRequirement('',{profile,budget,allowOver:false});for(const p of recommend(req,settings).filter(Boolean)){assert.ok(p.total<=budget);assert.equal(p.total,total(p.parts,settings));assert.ok(validate(p.parts).every(c=>c.ok));if(profile==='ai')assert.ok(p.parts.gpu.vram>=16)}}});
test('강화안 예산 초과는 명시적 허용시에만 가능하다',()=>{const req=parseRequirement('게임 200만 원',{allowOver:true});const plans=recommend(req,settings);assert.ok(plans[0].total<=req.budget);assert.ok(plans[1].total<=req.budget*1.1);assert.ok(plans[2].total<=req.budget*.9)});
test('저예산은 허위 견적을 만들지 않는다',()=>{assert.deepEqual(recommend(parseRequirement('게임 20만 원'),settings),[null,null,null])});
test('부품 교체로 발생한 전원 커넥터·GPU 간섭을 검출한다',()=>{const p=recommend(parseRequirement('게임 200만 원'),settings)[0];const parts={...p.parts,gpu:catalog.find(x=>x.id==='g4'),psu:catalog.find(x=>x.id==='p1'),case:catalog.find(x=>x.id==='k1')};assert.equal(validate(parts).find(x=>x.label==='GPU 길이').ok,false);assert.equal(validate(parts).find(x=>x.label==='보조 전원').ok,false);assert.equal(validate(parts).find(x=>x.label==='파워 용량').ok,false)});
test('미검수·품절 데이터는 추천에서 제외한다',()=>{const items=catalog.map(x=>({...x,verified:false}));assert.deepEqual(recommend(parseRequirement('게임 200만 원'),settings,items),[null,null,null])});
test('동일한 조합을 중복 반환하지 않는다',()=>{const plans=recommend(parseRequirement('게임 200만 원'),settings).filter(Boolean);assert.equal(new Set(plans.map(p=>Object.values(p.parts).map(x=>x.id).join('|'))).size,plans.length)});
test('잘못된 예산은 거부한다',()=>{assert.throws(()=>recommend({budget:NaN}));assert.throws(()=>recommend({budget:-1}))});
test('성능 강화안은 성능 또는 메모리 용량을 높여야 한다',()=>{for(const budget of [1000000,1500000,2000000,3000000]){const [a,b]=recommend(parseRequirement('게임',{budget,allowOver:true}),settings);if(a&&b)assert.ok(b.performance>a.performance||(b.performance===a.performance&&b.parts.ram.capacity>a.parts.ram.capacity))}});
test('실제 350만 원 카탈로그에서 가능한 경우에만 CPU·GPU 강화안을 제안한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync(new URL('../public/data/catalog.json',import.meta.url)));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const req=parseRequirement('게임 350만 원 화이트');const [balanced,enhanced]=recommend(req,settings,snapshot.parts);
 assert.ok(balanced);assert.ok(enhanced,'유효한 CPU/GPU 강화 쌍이 있으면 균형안을 조정해서라도 제공');if(enhanced){assert.ok(enhanced.performance>balanced.performance);assert.ok(enhanced.upgrades.some(change=>/^(CPU|GPU):/.test(change)));assert.ok(enhanced.total<=req.budget);}
});
test('게임은 CPU와 GPU가 같으면 메모리 증설만으로 강화안을 만들지 않는다',()=>{
 const ids=['c2','b1','r2','g2','s1','p2','k1','f1','o0'];
 const items=catalog.filter(p=>ids.includes(p.id));const ram=items.find(p=>p.category==='ram');
 items.push({...ram,id:'ram-upgrade',capacity:ram.capacity*2,price:ram.price+50000});
 const [balanced,enhanced]=recommend(parseRequirement('게임 200만 원'),settings,items);
 assert.ok(balanced);assert.equal(enhanced,null);
});

test('조합 생성 단계에서 BIOS 미확인 및 장착 불가 조합을 차단한다',()=>{
 const req=parseRequirement('게임 200만 원');const original=recommend(req,settings)[0];
 assert.ok(assembleBuild(original.parts,req,settings));
 const unknown={...original.parts,board:{...original.parts.board,bios:null}};
 assert.equal(assembleBuild(unknown,req,settings),null);
 const incompatible={...original.parts,case:{...original.parts.case,gpuLength:1}};
 assert.equal(assembleBuild(incompatible,req,settings),null);
 const items=catalog.map(p=>p.category==='board'?{...p,bios:null}:p);
 assert.deepEqual(recommend(req,settings,items),[null,null,null]);
});

test('후속 요청의 100만 원 상한이 이전 350만 원보다 우선한다',()=>{
 const req=parseRequirement('게임용 350만 원\n추가 요청: 100만원 이하에서 인터넷, 사무 업무를 볼 수 있는 컴퓨터');
 assert.equal(req.budget,1000000);assert.equal(req.profile,'office');
 for(const p of recommend(req,settings).filter(Boolean))assert.ok(p.total<=1000000);
 assert.equal(parseRequirement('350만원에서 900,000원으로 줄여줘').budget,900000);
});
test('카테고리의 13번째 고성능 후보도 예산 안이면 탐색한다',()=>{
 const low=catalog.find(p=>p.id==='g1');const better={...low,id:'thirteenth-gpu',price:low.price+12000,score:low.score+40};
 const items=[...catalog.filter(p=>p.category!=='gpu'),...Array.from({length:12},(_,i)=>({...low,id:'cheap-'+i,price:low.price+i})),better];
 const plans=recommend(parseRequirement('게임 300만 원'),settings,items).filter(Boolean);
 assert.ok(plans.some(p=>p.parts.gpu.id==='thirteenth-gpu'));
});

test('절약안은 언제나 균형안보다 저렴하다',()=>{for(const budget of [1000000,2000000,3500000,5000000]){const [a,,c]=recommend(parseRequirement('게임',{budget}),settings);if(a&&c)assert.ok(c.total<a.total)}});

test('실제 GPU의 다중 보조전원은 PSU 개수가 미확인이면 제외한다',()=>{
 const req=parseRequirement('게임 200만 원');const p=recommend(req,settings)[0];
 const parts={...p.parts,gpu:{...p.parts.gpu,dataMode:'live',connector:'8pin',connectorCount:2},psu:{...p.parts.psu,connectors:['8pin'],connectorCounts:null}};
 assert.equal(validate(parts).find(c=>c.label==='보조 전원').ok,null);
 parts.psu.connectorCounts={'8pin':2};assert.equal(validate(parts).find(c=>c.label==='보조 전원').ok,true);
});

test('인터넷 전용 요청은 사무용으로 해석하고 실제 카탈로그로 예산 내 견적을 만든다',async()=>{
 const {readFileSync}=await import('node:fs');
 const {hydrateSnapshot}=await import('../src/data-policy.mjs');
 const snapshot=JSON.parse(readFileSync(new URL('../public/data/catalog.json',import.meta.url)));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 for(const text of ['100만원 이하 인터넷 전용 컴퓨터 견적을 만들어줘','게임용 350만원 QHD\n추가 요청: 100만원 이하 인터넷 전용 컴퓨터 견적을 만들어줘']){
  const req=parseRequirement(text);assert.equal(req.profile,'office');assert.equal(req.resolution,'FHD');
  const [plan]=recommend(req,settings,hydrateSnapshot(snapshot).parts);
  assert.ok(plan);assert.ok(plan.total<=1000000);assert.equal(plan.parts.gpu.id,'g0');assert.ok(plan.checks.every(c=>c.ok===true));
 }
 assert.equal(parseRequirement('인터넷 게임용 150만원').profile,'gaming');
});

test('SSD 용량과 확인된 순차 속도 향상도 강화안으로 제안한다',()=>{
 const ids=['c4','b1','r1','g0','s1','p1','k1','f1','o0'];
 const base=catalog.filter(p=>ids.includes(p.id)).map(p=>p.category==='ssd'?{...p,readMBs:3000,writeMBs:2000}:p);
 const ssd=base.find(p=>p.category==='ssd');
 for(const upgrade of [{...ssd,id:'larger-ssd',capacity:2000,price:ssd.price+20000},{...ssd,id:'faster-ssd',readMBs:5000,writeMBs:4000,price:ssd.price+10000}]){
  const [a,b]=recommend(parseRequirement('100만원 이하 사무용'),settings,[...base,upgrade]);
  assert.ok(a);assert.ok(b,'SSD 업그레이드가 있는 강화안을 누락하면 안 된다');assert.equal(b.parts.ssd.id,upgrade.id);assert.match(b.upgrades.join(' '),/SSD/);assert.ok(b.total<=1000000);
 }
});

test('SSD 업그레이드는 기존 속도 사양을 낮추거나 미확인으로 바꾸지 않는다',()=>{
 const ids=['c4','b1','r1','g0','s1','p1','k1','f1','o0'];
 const base=catalog.filter(p=>ids.includes(p.id)).map(p=>p.category==='ssd'?{...p,readMBs:3000,writeMBs:2000}:p);
 const ssd=base.find(p=>p.category==='ssd');
 for(const spec of [{readMBs:null,writeMBs:null},{readMBs:5000,writeMBs:1000}]){
  const [,enhanced]=recommend(parseRequirement('100만원 사무용'),settings,[...base,{...ssd,...spec,id:'larger-but-slower',capacity:2000,price:ssd.price+10000}]);
  assert.equal(enhanced,null);
 }
 const external={...ssd,id:'external',name:'USB 외장 SSD',price:1000};
 const [plan]=recommend(parseRequirement('100만원 사무용'),settings,[...base,external]);assert.equal(plan.parts.ssd.id,ssd.id);
});
test('게임 강화안은 SSD만 바꿔 만들 수 없고 CPU나 GPU를 높여야 한다',()=>{
 const ids=['c2','b1','r2','g2','s1','p2','k1','f1','o0'];const items=catalog.filter(p=>ids.includes(p.id));const ssd=items.find(p=>p.category==='ssd');
 const [balanced,enhanced]=recommend(parseRequirement('게임 200만원'),settings,[...items,{...ssd,id:'bigger-ssd-only',capacity:2000,price:ssd.price+20000}]);assert.ok(balanced);assert.equal(enhanced,null);
 for(const budget of [1500000,2000000,3000000]){const [a,b]=recommend(parseRequirement(`게임 ${budget}원`),settings);if(a&&b){assert.ok(b.parts.cpu.score>a.parts.cpu.score||b.parts.gpu.score>a.parts.gpu.score);assert.ok(b.parts.cpu.score>=a.parts.cpu.score&&b.parts.gpu.score>=a.parts.gpu.score);}}
});
test('균형안이 예산을 거의 다 쓰면 모든 용도에서 균형안을 다시 골라 세 안을 제시한다',async()=>{
 const {selectProposals}=await import('../src/proposal-objectives.mjs');
 const build=(id,total,performance,cpu,gpu)=>({total,performance,checks:[],parts:{cpu:{id:'c'+cpu,score:cpu},board:{id:'b'},ram:{id:'r',capacity:32},gpu:{id:'g'+gpu,score:gpu,vram:8},ssd:{id:'s'+id,capacity:2000},psu:{id:'p'},case:{id:'k'},cooler:{id:'f'},os:{id:'o0'}}});
 // Balanced candidate at 99% of budget has nothing better within budget; a slightly slower base allows an upgrade.
 const combos=[build('top',1990000,100,70,60),build('base',1710000,90,66,40),build('gpu',1940000,94,66,60),build('cheap',1640000,85,60,40)];
 for(const profile of ['editing','office','ai']){
  const plans=selectProposals(combos,{profile,budget:2000000});
  assert.ok(plans.every(Boolean),profile);assert.ok(plans[1].upgrades.length>0);assert.ok(plans[1].total<=2000000);assert.ok(plans[2].total<plans[0].total);assert.equal(plans[0].selection.jointlySelected,true);
 }
});
test('예산 90% 이하 절약안이 없으면 균형안보다 저렴한 대체안을 목표 미달로 제시한다',async()=>{
 const {selectProposals}=await import('../src/proposal-objectives.mjs');
 const build=(id,total,performance)=>({total,performance,checks:[],parts:{cpu:{id:'c',score:50},board:{id:'b'},ram:{id:'r',capacity:16},gpu:{id:'g0',score:0,vram:0},ssd:{id:'s'+id,capacity:1000,readMBs:performance*10},psu:{id:'p'},case:{id:'k'},cooler:{id:'f'},os:{id:'o0'}}});
 const plans=selectProposals([build('a',999000,100),build('b',985000,90),build('c',960000,80)],{profile:'office',budget:1000000});
 assert.ok(plans[2]);assert.ok(plans[2].total<plans[0].total);assert.equal(plans[2].targetMet,false);
});
test('질문과 견적 요청을 구분하고 언급한 CPU·GPU 모델을 추출한다',async()=>{
 const {isQuestion,modelTokens}=await import('../src/question-answer.mjs');
 assert.equal(isQuestion('5060ti로 4k 게임을 돌릴수 있나?'),true);assert.equal(isQuestion('9800X3D랑 9700X 차이가 뭐야'),true);
 assert.equal(isQuestion('200만원 이하 adobe용 견적'),false);assert.equal(isQuestion('이 견적으로 배그 되나?'),true);assert.equal(isQuestion('강화안 견적 다시 짜줄 수 있어?'),false);assert.equal(isQuestion('PC 추천해 줄 수 있어?'),false);assert.equal(isQuestion('5060ti로 200만원 견적 짜줘?'),false);
 assert.deepEqual(modelTokens('RTX 5060 Ti 16GB, i5-14400F'),['5060ti','14400f']);assert.deepEqual(modelTokens('1080p 게임 200만원, 1440 모니터'),[]);
});
test('LLM 해석은 문장에 명시된 용도를 덮어쓰지 않고, 규칙이 못 찾은 용도만 채우며 예산 질문은 버린다',()=>{
 const llm={profile:'gaming',budget:2000000,resolution:'FHD',white:false,wifi:false,os:true,questions:['총 예산은 얼마인가요?','주로 쓰는 프로그램은?']};
 const adobe=mergeInterpretation('200만원 이하 adobe용 견적',llm);
 assert.equal(adobe.profile,'editing');assert.equal(adobe.budget,2000000);assert.equal(adobe.os,false);assert.deepEqual(adobe.questions,['주로 쓰는 프로그램은?']);
 assert.equal(mergeInterpretation('스타크래프트용 PC',{...llm,profile:'office'}).profile,'office');
});

test('budget in Korean numerals and X3D model names match the server rules (quote-eval scenarios)', () => {
  for (const [text, budget] of [['백오십만원으로 게임용', 1500000], ['2백만원 QHD 게임', 2000000], ['1.5백만원 FHD', 1500000],
    ['이백오십만 원', 2500000], ['1천5백만원', 15000000], ['1,800,000원', 1800000], ['150만원, 모니터 이원화', 1500000]])
    assert.equal(explicitBudget(text), budget, text);
  for (const [text, profile] of [['9800X3D로 350만원 4K 게이밍', 'gaming'], ['블렌더 3D 렌더링', 'editing'], ['캐드(CAD) 도면 작업', 'editing'],
    ['AutoCAD 작업용', 'editing'], ['스테이블 디퓨전 이미지 생성', 'ai']])
    assert.equal(detectProfile(text), profile, text);
});
