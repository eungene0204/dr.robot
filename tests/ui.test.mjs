import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
const bundle=await build({entryPoints:['src/main.jsx'],bundle:true,write:false,format:'iife',loader:{'.css':'empty'},define:{'process.env.NODE_ENV':'"production"'}});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const waitFor=async predicate=>{for(let i=0;i<100;i++){if(predicate())return;await wait(50)}assert.ok(predicate(),'화면 갱신 시간 초과');};
test('UI: 상담 → 3안 비교 → 호환성 재검증 → 견적서 발행',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});
 try{
 const w=dom.window;const savedQuotes=[];w.fetch=async(url,options={})=>{if(url==='/api/health')return {ok:true,json:async()=>({ok:true,mode:'demo'})};if(url==='/api/quotes'&&options.method==='POST'){const entry=JSON.parse(options.body);savedQuotes.push(entry);return {ok:true,json:async()=>entry}}if(url==='/api/quotes')return {ok:true,json:async()=>savedQuotes};throw new Error('offline demo')};w.crypto.randomUUID=()=>crypto.randomUUID();
 w.eval(bundle.outputFiles[0].text);await wait(60);
 const button=text=>[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes(text));
 assert.equal(w.document.documentElement.dataset.theme,'light');
 button('다크 모드').click();await wait(30);
 assert.equal(w.document.documentElement.dataset.theme,'dark');
 assert.equal(w.localStorage.getItem('dr-theme-v2'),null);
 button('라이트 모드').click();await wait(30);
 assert.equal(w.document.documentElement.dataset.theme,'light');
 assert.ok(w.document.querySelector('#request'));
 button('조건 설정').click();await wait(30);
 assert.equal(w.document.querySelectorAll('.profile-options .chosen').length,0);
 assert.equal(w.document.querySelector('#budget').value,'');
 assert.equal(w.document.querySelector('.resolution select').value,'');
 assert.equal(w.document.querySelectorAll('.composer-options input:checked').length,0);
 button('영상·3D').click();await wait(30);
 assert.equal(button('영상·3D').getAttribute('aria-pressed'),'true');
 button('영상·3D').click();await wait(30);
 assert.equal(w.document.querySelectorAll('.profile-options .chosen').length,0);
 assert.equal(w.document.querySelectorAll('.chat-message.user').length,0);
 button('조건 설정').click();await wait(30);
 button('배그 · 롤').click();await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 assert.equal(w.document.querySelectorAll('.plan-card').length,3);
 assert.equal(w.document.querySelector('.plan-card .plan-parts').querySelectorAll('.plan-part-row').length,9);
 assert.ok(w.document.querySelector('.plan-card .plan-part-name').textContent);
 assert.match(w.document.querySelector('.plan-card .plan-part-price').textContent,/원/);
 assert.equal(w.document.querySelectorAll('.chat-message.user').length,1);
 assert.equal(w.document.querySelectorAll('.chat-message.assistant').length,1);
 assert.equal(w.document.querySelector('#request').value,'');
 assert.ok(w.document.querySelector('table tbody'));
 const cpuSelect=w.document.querySelector('select[aria-label="최적 균형안 프로세서 교체"]');
 const originalCpu=cpuSelect.value;const originalTotal=w.document.querySelector('.plan-card .plan-price').textContent;
 w.document.querySelector('[aria-label="프로세서 대체 부품 목록"]').click();await wait(30);
 const replacements=[...w.document.querySelectorAll('.alternative-option')].filter(b=>!b.disabled);
 assert.ok(replacements.length>0);
 assert.ok([...w.document.querySelectorAll('.alternative-option:not(:disabled) .alternative-status')].every(node=>node.textContent.includes('규칙 통과')));
 const replacementName=replacements[0].querySelector('.alternative-title').textContent;
 replacements[0].click();await wait(40);
 assert.equal(w.document.querySelector('.alternatives-popover'),null);
 assert.notEqual(cpuSelect.value,originalCpu);
 assert.ok(w.document.querySelector('.plan-card .plan-parts').textContent.includes(replacementName));
 assert.notEqual(w.document.querySelector('.plan-card .plan-price').textContent,originalTotal);
 cpuSelect.value=originalCpu;cpuSelect.dispatchEvent(new w.Event('change',{bubbles:true}));await wait(30);

 assert.equal(button('선택안 견적서 발행').disabled,false);
 assert.equal(button('선택안 견적서 발행').disabled,false);
 button('선택안 견적서 발행').click();await wait(40);
 assert.ok(w.document.querySelector('.quote-modal'));
 assert.equal(savedQuotes.length,1);
 assert.equal(w.localStorage.getItem('bm-history'),null);
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
 button('배그 · 롤').click();await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 assert.ok(w.document.querySelector('.plan-price'));
 assert.ok(w.document.querySelector('.plan-meta').textContent.includes('Blender'));
 let opened;w.open=(...args)=>{opened=args};
 const preview=w.document.querySelector('.comparison .product-name-button');assert.ok(preview);preview.click();
 assert.match(opened[0],/https:\/\/prod\.danawa\.com\/info\/\?pcode=\d+/);
 assert.equal(opened[1],'_blank');assert.match(opened[2],/popup=yes/);
 w.document.querySelector('[aria-label="프로세서 대체 부품 목록"]').click();await wait(30);
 const search=w.document.querySelector('[aria-label="대체 부품 검색"]');
 const type=value=>{Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(search,value);search.dispatchEvent(new w.Event('input',{bubbles:true}));};
 type('9800X3D');await wait(30);assert.match(w.document.querySelector('.alternatives-list').textContent,/9800X3D/);
 type('285K');await wait(30);assert.match(w.document.querySelector('.alternatives-list').textContent,/285K/);
 assert.match(w.document.querySelector('.alternatives-list').textContent,/CPU 소켓/);
 const originalCpu=w.document.querySelector('select[aria-label="최적 균형안 프로세서 교체"]').value;
 assert.equal(w.document.querySelector('.alternatives-list .alternative-option').disabled,false);
 w.document.querySelector('.alternatives-list .alternative-option').click();await wait(30);
 assert.match(w.document.querySelector('.plan-card .plan-meta').textContent,/호환성 오류/);
 assert.equal(button('선택안 견적서 발행').disabled,true);
 const cpuSelect=w.document.querySelector('select[aria-label="최적 균형안 프로세서 교체"]');cpuSelect.value=originalCpu;cpuSelect.dispatchEvent(new w.Event('change',{bubbles:true}));await wait(30);


 assert.equal(button('선택안 견적서 발행').disabled,false);
 button('데이터 관리').click();await wait(40);
 assert.equal(w.document.querySelectorAll('.data-table tbody tr').length,snapshot.parts.filter(p=>!p.virtual).length);
 assert.ok(w.document.querySelector('.pipeline-panel').textContent.includes('8'));
 }finally{dom.window.close();}
});

test('UI: 인터넷 전용 100만원 요청으로 실제 견적서를 발행한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 w.fetch=async url=>({ok:true,json:async()=>String(url).includes('catalog')?snapshot:{}});
 w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
 const input=w.document.querySelector('#request');
 Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'100만원 이하 인터넷 전용 컴퓨터 견적을 만들어줘');
 input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 assert.match(w.document.querySelector('.results-heading').textContent,/사무·학습 · FHD/);
 const quotedPrice=w.document.querySelector('.plan-price').firstChild.textContent;
 assert.ok(Number(quotedPrice.replace(/\D/g,''))<=1000000);
 assert.match(w.document.querySelector('.plan-parts').textContent,/내장 그래픽/);
 const issue=[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('선택안 견적서 발행'));assert.equal(issue.disabled,false);issue.click();await wait(40);
 assert.ok(w.document.querySelector('.quote-modal'));assert.ok(w.document.querySelector('.quote-total').textContent.includes(quotedPrice));
 }finally{w.close();}
});

test('UI: 페이지가 다시 로드되어도 진행 중인 견적과 부품 선택을 복원한다',async()=>{
 const open=(session={})=>{const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;w.fetch=async()=>{throw new Error('offline demo')};w.crypto.randomUUID=()=>crypto.randomUUID();for(const [key,value]of Object.entries(session))w.sessionStorage.setItem(key,value);w.eval(bundle.outputFiles[0].text);return dom;};
 let dom=open();
 try{
 const w=dom.window;await wait(60);[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('배그 · 롤')).click();await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 const cpu=w.document.querySelector('select[aria-label="최적 균형안 프로세서 교체"]');const alternative=[...cpu.options].find(o=>!o.disabled&&o.value!==cpu.value);assert.ok(alternative);cpu.value=alternative.value;cpu.dispatchEvent(new w.Event('change',{bubbles:true}));await wait(30);
 const price=w.document.querySelector('.plan-price').textContent;
 const selectedCpu=cpu.value;const conversation=w.document.querySelector('.chat-messages').textContent;
 w.document.querySelectorAll('.plan-card')[2].click();await wait(30);const selectedPlan=w.document.querySelector('.plan-card.selected').getAttribute('aria-label');
 w.document.querySelector('.chat-scroll').scrollTop=320;w.document.querySelector('.chat-scroll').dispatchEvent(new w.Event('scroll'));await wait(30);
 w.dispatchEvent(new w.Event('pagehide'));
 const saved=Object.fromEntries(Array.from({length:w.sessionStorage.length},(_,i)=>{const key=w.sessionStorage.key(i);return [key,w.sessionStorage.getItem(key)];}));
 dom.window.close();dom=open(saved);await wait(120);
 assert.ok(dom.window.document.querySelector('.comparison'),'리로드 후 견적표가 사라지면 안 된다');
 assert.equal(dom.window.document.querySelector('.plan-price').textContent,price);
 assert.equal(dom.window.document.querySelector('select[aria-label="최적 균형안 프로세서 교체"]').value,selectedCpu);
 assert.equal(dom.window.document.querySelector('.chat-messages').textContent,conversation);
 assert.equal(dom.window.document.querySelector('.plan-card.selected').getAttribute('aria-label'),selectedPlan);
 assert.equal(dom.window.document.querySelector('.chat-scroll').scrollTop,320);
 const newQuote=[...dom.window.document.querySelectorAll('button')].find(b=>b.textContent.includes('새 견적 상담'));newQuote.click();await wait(30);
 const resetSaved=Object.fromEntries(Array.from({length:dom.window.sessionStorage.length},(_,i)=>{const key=dom.window.sessionStorage.key(i);return [key,dom.window.sessionStorage.getItem(key)];}));
 dom.window.close();dom=open(resetSaved);await wait(90);assert.ok(dom.window.document.querySelector('.chat-welcome'));assert.equal(dom.window.document.querySelector('.comparison'),null);
 }finally{dom.window.close();}
});
