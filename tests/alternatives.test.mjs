import test from 'node:test';
import assert from 'node:assert/strict';
import {catalog} from '../src/catalog.mjs';
import {parseRequirement,recommend} from '../src/engine.mjs';
import {alternativeOptions,compareSpecifications} from '../src/alternatives.mjs';
const req=parseRequirement('게임 350만원');const settings={assembly:30000};const plan=recommend(req,settings)[0];
test('상위·다른 플랫폼·미확인 부품도 숨기지 않고 교체 조건을 표시한다',()=>{
 const cpu=plan.parts.cpu;
 const incompatible={...cpu,id:'intel-ultra',name:'Intel Core Ultra 9 285K',socket:'LGA1851',price:900000};
 const unknown={...cpu,id:'amd-x3d',name:'Ryzen 7 9800X3D',price:600000};
 const options=alternativeOptions([...catalog,incompatible,unknown],'cpu',plan,req,settings);
 const intel=options.find(x=>x.part.id===incompatible.id),amd=options.find(x=>x.part.id===unknown.id);
 assert.equal(intel.selectable,false);assert.ok(intel.reasons.some(r=>r.includes('CPU 소켓')));
 assert.equal(amd.selectable,false);assert.ok(amd.reasons.some(r=>r.includes('BIOS')));
 assert.ok(options.some(x=>x.selectable));
});
test('가격·벤치마크 미수집 제품은 보여주되 교체할 수 없다',()=>{
 const p={...plan.parts.cpu,id:'missing-live',dataMode:'live',price:null,benchmark:null};
 const [option]=alternativeOptions([p],'cpu',plan,req,settings);
 assert.equal(option.selectable,false);assert.equal(option.total,null);assert.ok(option.reasons.includes('가격 갱신 필요'));assert.ok(option.reasons.includes('실측 벤치마크 확인 필요'));
});
test('용량·사양순 정렬은 저가와 상위 등급을 모두 유지한다',()=>{
 for(const category of ['ram','ssd','psu']){
  const options=alternativeOptions(catalog,category,plan,req,settings).sort(compareSpecifications);
  assert.equal(options.length,catalog.filter(x=>x.category===category).length);
  assert.equal(options[0].part.capacity,Math.max(...options.map(x=>x.part.capacity)));
 }
});
