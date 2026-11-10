import test from 'node:test';
import assert from 'node:assert/strict';
import {parseRequirement,recommend,validateBuild} from '../src/engine.mjs';
import {catalog} from '../src/catalog.mjs';
test('용도만 요청하면 예산은 null이고 명시한 금액만 상한으로 쓴다',()=>{assert.equal(parseRequirement('4K 게임용 PC').budget,null);assert.equal(parseRequirement('4K 게임 200만원').budget,2000000);assert.equal(parseRequirement('200만원 게임\n추가 요청: 예산 제한 없이 최고 성능').budget,null)});
test('상한 없는 견적은 200만원으로 제한하지 않으며 명시적 예산은 지킨다',()=>{const expensive=catalog.map(p=>({...p,price:p.price*3}));const req=parseRequirement('4K 게임');const best=recommend(req,{assembly:30000},expensive)[0];assert.ok(best);assert.ok(best.total>2000000);assert.equal(best.selection.budgetMode,'unlimited');assert.ok(recommend(parseRequirement('4K 게임 200만원'),{assembly:30000},expensive).filter(Boolean).every(p=>p.total<=2000000));});
test('Optane 캐시와 작은 보조 저장장치는 주 드라이브로 추천하지 않는다',()=>{const base=recommend(parseRequirement('게임 200만원'),{assembly:30000},catalog)[0];const small={...base.parts.ssd,id:'small-cache',name:'인텔 Optane Memory M.2 NVMe (16GB)',capacity:16,price:1000};assert.equal(validateBuild({...base.parts,ssd:small},parseRequirement('4K 게임')).every(c=>c.ok===true),false)});
test('무예산 4K 게임은 허용 후보의 GPU 성능을 우선한다',()=>{const plans=recommend(parseRequirement('4K 게임'),{assembly:30000},catalog);const best=plans[0];assert.ok(best);assert.ok(best.parts.ssd.capacity>=2000);assert.ok(plans.every(Boolean),'예산이 없어도 세 안을 제시한다');assert.ok(plans[1].upgrades.some(u=>/^(CPU|GPU):/.test(u)),'강화안은 용량만이 아닌 CPU/GPU 향상');assert.ok(plans[2].total<best.total);});

test('예산 미지정은 최상급 GPU가 아니라 용도 충족 범위에서 고른다',async()=>{
 const {selectProposals}=await import('../src/proposal-objectives.mjs');
 const base=recommend(parseRequirement('게임 200만원'),{assembly:30000},catalog)[0];assert.ok(base);
 const make=(id,cpu,gpu,total)=>({...base,total,performance:cpu*.25+gpu*.75,parts:{...base.parts,cpu:{...base.parts.cpu,id:`c-${id}`,score:cpu},gpu:{...base.parts.gpu,id:`g-${id}`,name:id==='flagship'?'RTX 5090':'적정 GPU',score:gpu}}});
 const combos=[make('cheap',80,100,1000000),make('balanced',100,100,1120000),make('enhanced',100,140,1350000),make('flagship',150,347,5000000)];
 const req={profile:'gaming',budget:null,resolution:'QHD',text:'오버워치용 견적'};
 const normal=selectProposals(combos,req);assert.ok(normal.every(Boolean));assert.ok(normal.every(p=>p.parts.gpu.id!=='g-flagship'));
 assert.ok(selectProposals(combos,{...req,text:'예산 제한 없이 최고 성능'}).some(p=>p?.parts.gpu.id==='g-flagship'));
 assert.ok(selectProposals([combos.at(-1)],req,{gpuReferenceScore:100}).every(p=>p===null),'적정 후보가 없다고 플래그십으로 승급하지 않는다');
});
