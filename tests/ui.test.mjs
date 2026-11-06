import {recommend as buildRecommendations} from '../src/engine.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
const bundle=await build({entryPoints:['src/main.jsx'],bundle:true,write:false,format:'iife',loader:{'.css':'empty'},define:{'process.env.NODE_ENV':'"production"'}});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
const waitFor=async predicate=>{for(let i=0;i<100;i++){if(predicate())return;await wait(50)}assert.ok(predicate(),'화면 갱신 시간 초과');};
const apiMock=(snapshot,mode='live',state={})=>async(url,options={})=>{
 const method=options.method||'GET';let value=null;
 if(url==='/api/health')value={ok:true,mode,llm:Boolean(state.answer)};
 else if(url==='/api/answer')value=state.answer(JSON.parse(options.body));
 else if(String(url).includes('/catalog'))value=snapshot;
 else if(url==='/api/recommend/fresh'){const data=JSON.parse(options.body);value={plans:buildRecommendations(data.requirement,data.settings,snapshot.parts),catalogVersion:snapshot.catalogVersion};}
 else if(url==='/api/settings'){if(method==='PUT')state.settings=JSON.parse(options.body);value=state.settings||null;}
 else if(String(url).startsWith('/api/state/')){if(method==='PUT')state[url]=JSON.parse(options.body);value=state[url]||null;}
 else if(url==='/api/quotes'){state.quotes??=[];if(method==='POST'){value={...JSON.parse(options.body),id:crypto.randomUUID()};state.quotes.push(value)}else value=state.quotes;}
 else value={};return {ok:true,json:async()=>structuredClone(value)};
};
const cpuName=w=>w.document.querySelector('.plan-card .plan-part-name').textContent;
async function restoreCpu(w,name){
 w.document.querySelector('[aria-label="대체 부품 목록 닫기"]')?.click();await wait(10);
 w.document.querySelector('[aria-label="최적 균형안 프로세서 교체"]').click();await wait(30);
 const input=w.document.querySelector('[aria-label="대체 부품 검색"]');Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(input,name);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
 const item=[...w.document.querySelectorAll('.alternative-option')].find(b=>b.querySelector('.alternative-title').textContent===name);assert.ok(item,`원래 CPU ${name}`);item.click();await wait(30);
}
test('UI: 상담 → 3안 비교 → 호환성 재검증 → 견적서 발행',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});
 try{
 const w=dom.window;const savedQuotes=[];w.fetch=async(url,options={})=>{if(url==='/api/health')return {ok:true,json:async()=>({ok:true,mode:'demo'})};if(url==='/api/quotes'&&options.method==='POST'){const entry=JSON.parse(options.body);savedQuotes.push(entry);return {ok:true,json:async()=>entry}}if(url==='/api/quotes')return {ok:true,json:async()=>savedQuotes};throw new Error('offline demo')};w.crypto.randomUUID=()=>crypto.randomUUID();
 w.eval(bundle.outputFiles[0].text);await waitFor(()=>w.document.documentElement.dataset.theme);
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
 const originalCpu=cpuName(w);const originalTotal=w.document.querySelector('.plan-card .plan-price').textContent;
 w.document.querySelector('[aria-label="프로세서 대체 부품 목록"]').click();await wait(30);
 const replacements=[...w.document.querySelectorAll('.alternative-option')].filter(b=>!b.disabled);
 assert.ok(replacements.length>0);
 assert.ok([...w.document.querySelectorAll('.alternative-option:not(:disabled) .alternative-status')].every(node=>node.textContent.includes('규칙 통과')));
 const replacementName=replacements[0].querySelector('.alternative-title').textContent;
 replacements[0].click();await wait(40);
 assert.equal(w.document.querySelector('.alternatives-popover'),null);
 assert.notEqual(cpuName(w),originalCpu);
 assert.ok(w.document.querySelector('.plan-card .plan-parts').textContent.includes(replacementName));
 assert.notEqual(w.document.querySelector('.plan-card .plan-price').textContent,originalTotal);
 await restoreCpu(w,originalCpu);
 w.document.querySelector('[aria-label="최적 균형안 CPU 쿨러 교체"]').click();await wait(30);
 const coolingTabs=w.document.querySelector('[aria-label="쿨러 냉각 방식"]');assert.ok(coolingTabs);
 const air=[...coolingTabs.querySelectorAll('button')].find(b=>b.textContent==='공랭');air.click();await wait(30);assert.equal(air.getAttribute('aria-selected'),'true');assert.ok(w.document.querySelectorAll('.alternative-option').length>0);assert.match(w.document.querySelector('.alternatives-list').textContent,/공랭/);
 [...coolingTabs.querySelectorAll('button')].find(b=>b.textContent==='수랭').click();await wait(30);assert.equal(w.document.querySelectorAll('.alternative-option').length,0);assert.match(w.document.querySelector('.alternatives-empty').textContent,/필터/);w.document.querySelector('[aria-label="대체 부품 목록 닫기"]').click();await wait(30);


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
 w.fetch=apiMock(snapshot);
 w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
 await waitFor(()=>w.document.querySelector('.demo-status')?.textContent.includes(`실제 상품 ${snapshot.parts.filter(p=>!p.virtual).length}개`));
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
 const originalCpu=cpuName(w);
 assert.equal(w.document.querySelector('.alternatives-list .alternative-option').disabled,false);
 w.document.querySelector('.alternatives-list .alternative-option').click();await wait(30);
 assert.match(w.document.querySelector('.plan-card .plan-meta').textContent,/호환성 오류/);
 assert.equal(button('선택안 견적서 발행').getAttribute('aria-disabled'),'true');
 await restoreCpu(w,originalCpu);


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
 w.fetch=apiMock(snapshot);
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

test('UI: DB 상태 API에서 진행 중인 상담과 부품 선택을 복원한다',async()=>{
 const state={};const open=()=>{const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});dom.window.fetch=apiMock(null,'demo',state);dom.window.crypto.randomUUID=()=>crypto.randomUUID();dom.window.eval(bundle.outputFiles[0].text);return dom;};
 let dom=open();try{const w=dom.window;await wait(90);[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('배그 · 롤')).click();await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 w.document.querySelector('[aria-label="최적 균형안 프로세서 교체"]').click();await wait(30);const option=[...w.document.querySelectorAll('.alternative-option')].find(b=>!b.disabled&&b.textContent.includes('등록된 호환성 규칙 통과'));assert.ok(option);option.click();await wait(40);
 const price=w.document.querySelector('.plan-price').textContent;const selectedCpu=cpuName(w);const conversation=w.document.querySelector('.chat-messages').textContent;
 w.document.querySelectorAll('.plan-card')[2].click();await wait(30);const selectedPlan=w.document.querySelector('.plan-card.selected').getAttribute('aria-label');
 w.document.querySelector('.chat-scroll').scrollTop=320;w.document.querySelector('.chat-scroll').dispatchEvent(new w.Event('scroll'));w.dispatchEvent(new w.Event('pagehide'));await wait(500);assert.ok(state['/api/state/consult-demo']);assert.equal(w.sessionStorage.length,0);
 dom.window.close();dom=open();await wait(150);const rw=dom.window;assert.ok(rw.document.querySelector('.comparison'));assert.equal(rw.document.querySelector('.plan-price').textContent,price);assert.equal(cpuName(rw),selectedCpu);assert.equal(rw.document.querySelector('.chat-messages').textContent,conversation);assert.equal(rw.document.querySelector('.plan-card.selected').getAttribute('aria-label'),selectedPlan);assert.equal(rw.document.querySelector('.chat-scroll').scrollTop,320);
 [...rw.document.querySelectorAll('button')].find(b=>b.textContent.includes('새 견적 상담')).click();await wait(500);dom.window.close();dom=open();await wait(120);assert.ok(dom.window.document.querySelector('.chat-welcome'));assert.equal(dom.window.document.querySelector('.comparison'),null);
 }finally{dom.window.close()}
});
test('UI: 예산 없는 4K 요청을 상한 없이 생성·발행하고 제한 없음으로 표시한다',async()=>{const state={};const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await waitFor(()=>w.document.querySelector('#request'));const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'4K 게임용 PC');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));assert.match(w.document.querySelector('.chat-messages').textContent,/예산 제한 없음/);assert.doesNotMatch(w.document.querySelector('.results').textContent,/Infinity|NaN/);assert.match(w.document.querySelector('.plan-price').textContent,/예산 제한 없이 성능 우선/);const issue=[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('선택안 견적서 발행'));issue.click();await waitFor(()=>w.document.querySelector('.quote-modal'));assert.equal(state.quotes[0].req.budget,null);assert.match(w.document.querySelector('.quote-summary').textContent,/예산 제한 없음/);assert.ok(state.quotes[0].plan.parts.ssd.capacity>=2000);}finally{w.close()}});
test('UI: 견적 뒤 질문은 기존 견적 아래에 답만 이어 붙이고, 용도가 바뀐 견적 요청은 이전 예산을 쓰지 않는다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 w.fetch=apiMock(snapshot);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
 const send=async value=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));};
 await send('200만원 이하 adobe용 견적');await waitFor(()=>w.document.querySelector('.plan-price'));
 assert.match(w.document.querySelector('.results-heading').textContent,/영상·3D/);
 const quoteSection=w.document.querySelector('.results');
 await send('5060ti로 4k 게임을 플레이 할 수 있나?');await waitFor(()=>w.document.querySelectorAll('.chat-messages.after-results .chat-message.assistant').length===1);
 const after=w.document.querySelector('.chat-messages.after-results');
 const answer=after.querySelector('.chat-message.assistant p').textContent;
 assert.match(answer,/RTX 5060 Ti/);assert.match(answer,/FPS 실측 자료가 없어/);assert.doesNotMatch(answer,/2,000,000원|견적/);
 assert.equal(w.document.querySelector('.results'),quoteSection,'질문은 기존 견적을 다시 그리지 않음');
 assert.match(quoteSection.textContent,/영상·3D/);assert.equal(w.document.querySelectorAll('.results').length,1);
 assert.ok(quoteSection.compareDocumentPosition(after)&w.Node.DOCUMENT_POSITION_FOLLOWING,'답변은 견적 아래에 표시');
 assert.equal(after.querySelectorAll('button').length,0,'질문 답변에는 견적 버튼이 없음');
 await send('5060ti 게임 4K 견적');await waitFor(()=>/게임 · 4K/.test(w.document.querySelector('.results-heading').textContent));
 const reply=[...w.document.querySelectorAll('.chat-message.assistant p')].at(-1).textContent;
 assert.doesNotMatch(reply,/2,000,000원/);assert.match(reply,/예산 제한 없음/);
 const gpus=[...w.document.querySelectorAll('[aria-label$="부품 구성"]')].map(card=>card.textContent);
 assert.ok(gpus.length>0&&gpus.every(text=>/5060 Ti/i.test(text)),'모든 안이 요청한 GPU를 포함');
 assert.equal(w.document.querySelectorAll('.chat-messages.after-results').length,0,'새 견적은 마지막 답변 아래로 이동');
}finally{w.close();}
});

test('UI: LLM이 켜져 있으면 질문을 현재 견적 부품 id·최근 대화와 함께 답변 API로 보내고 근거 종류를 표시한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 const sent=[];const state={answer:body=>{sent.push(body);return {text:'일반적으로 4K에서는 옵션 조정이 필요해요.',sources:['quote','general'],method:'llm'};}};
 try{
 w.fetch=apiMock(snapshot,'live',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
 const send=async value=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));};
 await send('200만원 게임용 견적');await waitFor(()=>w.document.querySelector('.plan-price'));
 await send('이 견적으로 4k 게임 되나?');await waitFor(()=>w.document.querySelector('.message-sources'));
 assert.equal(sent.length,1);assert.equal(sent[0].text,'이 견적으로 4k 게임 되나?');
 assert.equal(sent[0].quote.req.profile,'gaming');assert.equal(typeof sent[0].quote.plans[0].parts.gpu,'string');
 assert.deepEqual(sent[0].history.map(m=>m.role),['user','assistant']);
 const after=w.document.querySelector('.chat-messages.after-results');
 assert.match(after.textContent,/옵션 조정이 필요해요/);assert.match(after.querySelector('.message-sources').textContent,/현재 견적 · 일반 지식/);
 }finally{w.close();}
});
