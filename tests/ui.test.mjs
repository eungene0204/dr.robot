import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
const bundle=await build({entryPoints:['src/main.jsx'],bundle:true,write:false,format:'iife',loader:{'.css':'empty'},define:{'process.env.NODE_ENV':'"production"'}});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
test('UI: 상담 → 3안 비교 → 호환성 재검증 → 견적서 발행',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});
 try{
 const w=dom.window;w.fetch=async()=>{throw new Error('offline demo')};w.crypto.randomUUID=()=>crypto.randomUUID();
 w.eval(bundle.outputFiles[0].text);await wait(60);
 const button=text=>[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes(text));
 assert.equal(w.document.documentElement.dataset.theme,'dark');
 button('라이트 모드').click();await wait(30);
 assert.equal(w.document.documentElement.dataset.theme,'light');
 assert.equal(JSON.parse(w.localStorage.getItem('dr-theme')),'light');
 button('다크 모드').click();await wait(30);
 assert.equal(w.document.documentElement.dataset.theme,'dark');
 assert.ok(w.document.querySelector('#request'));
 button('조건 설정').click();await wait(30);
 button('영상·3D').click();await wait(30);
 assert.equal(w.document.querySelectorAll('.chat-message.user').length,0);
 button('조건 설정').click();await wait(30);
 button('배그 · 롤').click();await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(800);
 assert.equal(w.document.querySelectorAll('.plan-card').length,3);
 assert.equal(w.document.querySelector('.plan-card .plan-parts').querySelectorAll('.plan-part-row').length,10);
 assert.ok(w.document.querySelector('.plan-card .plan-part-name').textContent);
 assert.match(w.document.querySelector('.plan-card .plan-part-price').textContent,/원/);
 assert.equal(w.document.querySelectorAll('.chat-message.user').length,1);
 assert.equal(w.document.querySelectorAll('.chat-message.assistant').length,1);
 assert.equal(w.document.querySelector('#request').value,'');
 assert.ok(w.document.querySelector('table tbody'));
 const select=w.document.querySelector('select[aria-label="최적 균형안 파워서플라이 교체"]');
 const gpu=w.document.querySelector('select[aria-label="최적 균형안 그래픽카드 교체"]');
 gpu.value='g4';gpu.dispatchEvent(new w.Event('change',{bubbles:true}));
 select.value='p1';select.dispatchEvent(new w.Event('change',{bubbles:true}));await wait(40);
 assert.ok(button('선택안 견적서 발행').disabled);
 gpu.value='g2';gpu.dispatchEvent(new w.Event('change',{bubbles:true}));
 select.value='p2';select.dispatchEvent(new w.Event('change',{bubbles:true}));await wait(40);
 assert.equal(button('선택안 견적서 발행').disabled,false);
 button('선택안 견적서 발행').click();await wait(40);
 assert.ok(w.document.querySelector('.quote-modal'));
 assert.ok(w.document.querySelector('.quote-warning').textContent.includes('가상 가격'));
 assert.equal(JSON.parse(w.localStorage.getItem('bm-history')).length,1);
 w.document.querySelector('[aria-label="닫기"]').click();await wait(30);
 button('새 견적 상담').click();await wait(30);
 assert.equal(w.document.querySelectorAll('.chat-message').length,0);
 assert.equal(w.document.querySelectorAll('.plan-card').length,0);
 assert.ok(w.document.querySelector('.chat-welcome'));
 }finally{dom.window.close();}
});
test('UI: 기본 모드는 실제 스냅샷을 로드하고 출처·가격·벤치마크를 사용한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 w.fetch=async url=>{if(String(url).includes('catalog'))return {ok:true,json:async()=>snapshot};return {ok:true,json:async()=>({})}};
 w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
 assert.ok(w.document.querySelector('.demo-status').textContent.includes(`실제 상품 ${snapshot.parts.filter(p=>!p.virtual).length}개`));
 const button=text=>[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes(text));
 button('배그 · 롤').click();await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(800);
 assert.ok(w.document.querySelector('.plan-price'));
 assert.ok(w.document.querySelector('.plan-meta').textContent.includes('Blender'));
 assert.ok(button('선택안 견적서 발행').disabled);
 button('데이터 관리').click();await wait(40);
 assert.equal(w.document.querySelectorAll('.data-table tbody tr').length,snapshot.parts.filter(p=>!p.virtual).length);
 assert.ok(w.document.querySelector('.pipeline-panel').textContent.includes('8'));
 }finally{dom.window.close();}
});
