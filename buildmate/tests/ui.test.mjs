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
 else if(url==='/api/requirements')value=state.requirements?.(JSON.parse(options.body))??{};
 else if(String(url).includes('/catalog'))value=snapshot;
 else if(url==='/api/agent/quote'){const data=JSON.parse(options.body);value={status:'completed',quote:{plans:buildRecommendations(data.requirement,{assembly:data.assembly},snapshot.parts),catalogVersion:snapshot.catalogVersion}};}
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
 button('영상·방송·3D').click();await wait(30);
 assert.equal(button('영상·방송·3D').getAttribute('aria-pressed'),'true');
 button('영상·방송·3D').click();await wait(30);
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
 const restore=()=>w.document.querySelector('[aria-label="최적 균형안 최초 추천으로 되돌리기"]');
 assert.ok(restore()?.disabled,'교체 전에는 되돌리기 버튼 비활성');
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
 assert.equal(restore().disabled,false,'교체 후 되돌리기 버튼 활성');
 restore().click();await wait(40);
 assert.equal(cpuName(w),originalCpu,'최초 추천 CPU로 복원');
 assert.equal(w.document.querySelector('.plan-card .plan-price').textContent,originalTotal,'최초 추천 합계로 복원');
 assert.ok(restore().disabled,'복원 후 다시 비활성');
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
test('UI: 예산 없는 4K 요청을 상한 없이 생성·발행하고 제한 없음으로 표시한다',async()=>{const state={};const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await waitFor(()=>w.document.querySelector('#request'));const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'4K 게임용 PC');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));assert.match(w.document.querySelector('.chat-messages').textContent,/예산 제한 없음/);assert.doesNotMatch(w.document.querySelector('.results').textContent,/Infinity|NaN/);assert.match(w.document.querySelector('.plan-price').textContent,/용도에 맞춘 적정 사양/);const issue=[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('선택안 견적서 발행'));issue.click();await waitFor(()=>w.document.querySelector('.quote-modal'));assert.equal(state.quotes[0].req.budget,null);assert.match(w.document.querySelector('.quote-summary').textContent,/예산 제한 없음/);assert.ok(state.quotes[0].plan.parts.ssd.capacity>=2000);assert.match(w.document.querySelector('.results-note').textContent,/^요구 해석: 규칙 기반\. 표시된 대체 지수는/);}finally{w.close()}});
test('UI: 견적 뒤 질문은 기존 견적 아래에 답만 이어 붙이고, 용도가 바뀐 견적 요청은 이전 예산을 쓰지 않는다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 w.fetch=apiMock(snapshot);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
 const send=async value=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));};
 await send('200만원 이하 adobe용 견적');await waitFor(()=>w.document.querySelector('.plan-price'));
 assert.match(w.document.querySelector('.results-heading').textContent,/영상·방송·3D/);
 const quoteSection=w.document.querySelector('.results');
 await send('5060ti로 4k 게임을 플레이 할 수 있나?');await waitFor(()=>w.document.querySelectorAll('.chat-messages.after-results .chat-message.assistant').length===1);
 const after=w.document.querySelector('.chat-messages.after-results');
 const answer=after.querySelector('.chat-message.assistant p').textContent;
 assert.match(answer,/RTX 5060 Ti/);assert.match(answer,/FPS 실측 자료가 없어/);assert.doesNotMatch(answer,/2,000,000원|견적/);
 assert.equal(w.document.querySelector('.results'),quoteSection,'질문은 기존 견적을 다시 그리지 않음');
 assert.match(quoteSection.textContent,/영상·방송·3D/);assert.equal(w.document.querySelectorAll('.results').length,1);
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
test('UI: pcquote 견적은 예산 +5% 안이면 발행할 수 있고, 부품 교체·대체 후보는 pcquote 규칙으로 다시 검사한다',async()=>{
 const {readFileSync}=await import('node:fs');
 const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){p.dataMode='live';if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 // A pcquote-style answer built from a valid build whose total sits above the stated budget but inside +5%.
 const base=buildRecommendations({profile:'office',budget:1000000,resolution:'FHD'},{assembly:30000},snapshot.parts).find(Boolean);
 const budgetMan=Math.floor(base.total/1.02/10000);
 assert.ok(base.total>budgetMan*10000&&base.total<=budgetMan*10000*1.05,`fixture total ${base.total}`);
 // The server's response shape for a pcquote plan (pcquote/backend/src/pcquote/screen.py map_plan).
 const serverPlan=req=>({...base,id:'balanced',engine:'pcquote',catalogVersion:snapshot.catalogVersion,budgetCap:Math.floor(req.budget*1.05),
  checks:[{label:'칩셋 세대 지원 (출고 전 확인)',ok:true,detail:'BIOS 업데이트 후 지원',warning:true}],
  parts:{...base.parts,board:{...base.parts.board,biosPreparation:'출고 전 확인: BIOS 업데이트 후 지원'}}});
 const otherBoard=snapshot.parts.find(p=>p.category==='board'&&p.id!==base.parts.board.id&&p.socket===base.parts.board.socket);
 const calls=[];const state={};const mock=apiMock(snapshot,'live',state);
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
  w.fetch=async(url,options={})=>{
   if(url==='/api/agent/quote'){const data=JSON.parse(options.body);return {ok:true,json:async()=>({status:'completed',quote:{plans:[serverPlan(data.requirement),null,null],catalogVersion:snapshot.catalogVersion,engine:'pcquote'}})};}
   if(url==='/api/quotes/alternatives'){calls.push(['alternatives',JSON.parse(options.body)]);return {ok:true,json:async()=>({items:[{id:otherBoard.id}]})};}
   if(url==='/api/quotes/evaluate'){const body=JSON.parse(options.body);calls.push(['evaluate',body]);return {ok:true,json:async()=>({checks:[{label:'CPU 소켓',ok:true,detail:'pcquote'}],performance:41,popularity:0.4,warnings:[]})};}
   return mock(url,options);
  };
  w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(120);
  const input=w.document.querySelector('#request');
  Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,`사무용 PC ${budgetMan}만원`);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
  w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
  assert.match(w.document.body.textContent,/출고 전 확인: BIOS 업데이트 후 지원/);
  const issue=()=>[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('선택안 견적서 발행'));
  assert.equal(issue().disabled,false,'예산 +5% 안 pcquote 견적은 발행 가능');
  w.document.querySelector('[aria-label="최적 균형안 메인보드 교체"]').click();
  await waitFor(()=>calls.some(c=>c[0]==='alternatives')&&w.document.querySelector('.alternative-option'));
  assert.equal(calls.find(c=>c[0]==='alternatives')[1].category,'board');
  const input2=w.document.querySelector('[aria-label="대체 부품 검색"]');Object.getOwnPropertyDescriptor(w.HTMLInputElement.prototype,'value').set.call(input2,otherBoard.name);input2.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
  const option=[...w.document.querySelectorAll('.alternative-option')].find(b=>b.querySelector('.alternative-title').textContent===otherBoard.name);
  assert.ok(option,'pcquote가 호환으로 본 보드가 목록에 있다');assert.doesNotMatch(option.textContent,/조건 불충족/);
  option.click();await waitFor(()=>calls.some(c=>c[0]==='evaluate'));
  assert.equal(calls.find(c=>c[0]==='evaluate')[1].parts.board,otherBoard.id);
  assert.equal(calls.find(c=>c[0]==='evaluate')[1].refreshPartId,otherBoard.id);
  await waitFor(()=>w.document.querySelector('.plan-card').textContent.includes(otherBoard.name));
  assert.doesNotMatch(w.document.body.textContent,/출고 전 확인: BIOS 업데이트 후 지원/);
 }finally{w.close();}
});
test('UI: 결과 안내문에 요구 해석이 LLM 기반인지 규칙 기반인지 표시하고, LLM 실패는 드러내지 않는다',async()=>{
 for(const [requirements,label] of [[()=>({method:'openrouter',profile:'gaming',resolution:'QHD',questions:[]}),'요구 해석: LLM 기반.'],[()=>({method:'exaone',profile:'gaming',resolution:'QHD',questions:[]}),'요구 해석: LLM 기반.'],[()=>({method:'local',fallback:'LLM 응답 오류 (429)',questions:[]}),'요구 해석: 규칙 기반.']]){
  const state={answer:()=>({text:'',sources:[]}),requirements};const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
  try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await waitFor(()=>w.document.querySelector('#request'));
   const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,requirements().method==='local'?'150만원 QHD 게임용':'배틀그라운드용 150만원 QHD');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
   w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.results-note'));
   const strong=w.document.querySelector('.results-note .interpretation');assert.equal(strong?.textContent.trim(),label);
   assert.doesNotMatch(w.document.querySelector('.results').outerHTML,/실패|오류|429/);  // customers share this screen
  }finally{w.close()}}
});

test('UI EXAONE: 용도 미확인 시 견적을 멈추고 답변 후 원래 예산으로 재개한다',async()=>{
 const prompts=[];const state={answer:()=>({text:'',sources:[]}),requirements:({text})=>{prompts.push(text);return text.includes('사무용')?{method:'local',profile:'office',budget:1500000,resolution:'FHD',questions:[]}:{method:'local',profile:null,needsPurpose:true,questions:['주로 어떤 용도로 쓰실 예정인가요?']};}};
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  const send=async value=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(30);await waitFor(()=>!w.document.querySelector('.chat-send .spin'));};
  await send('LaTeX로 논문을 작성할 본체 150만원');
  assert.equal(w.document.querySelectorAll('.plan-card').length,0,'용도를 모르면 게임용 견적을 만들지 않는다');
  assert.equal(w.document.querySelector('.clarify'),null);assert.match(w.document.querySelector('.chat-messages').textContent,/주로 어떤 용도/);
  await send('사무용이에요');await waitFor(()=>w.document.querySelector('.plan-card'));
  assert.equal(prompts.length,1,'명확해진 후속 요청은 해석 API를 생략한다');
  await waitFor(()=>state['/api/state/consult-demo']?.req?.profile==='office');
  assert.match(state['/api/state/consult-demo'].req.text,/LaTeX.*150만원[\s\S]*사무용/);
  assert.match(w.document.querySelector('.results-heading').textContent,/사무·학습.*FHD/);
  assert.match([...w.document.querySelectorAll('.chat-message.assistant')].at(-1).textContent,/1,500,000원/);
 }finally{w.close();}
});

test('UI EXAONE: 규칙에 없는 LaTeX의 정상 LLM 용도를 자동 게임 기본값으로 덮어쓰지 않는다',async()=>{
 const state={answer:()=>({text:'',sources:[]}),requirements:()=>({method:'exaone',profile:'office',budget:1500000,resolution:'FHD',questions:[]})};
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'LaTeX로 논문을 작성할 본체 150만원');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-card'));
  assert.match(w.document.querySelector('.results-heading').textContent,/사무·학습.*FHD/);
 }finally{w.close();}
});

test('UI EXAONE: 서버 대기 정책에 따라 55초 해석 응답도 받아 견적을 만든다',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 let now=0;const timers=[];w.AbortSignal.timeout=ms=>{const c=new w.AbortController();timers.push({at:now+ms,c});return c.signal;};
 const advance=ms=>{now+=ms;for(const t of timers)if(t.at<=now)t.c.abort(new w.DOMException('시간 초과','TimeoutError'));};
 const state={answer:()=>({text:'',sources:[]})};const mock=apiMock(null,'demo',state);
 try{w.fetch=async(url,options={})=>{
   if(url==='/api/health')return {ok:true,json:async()=>({ok:true,mode:'demo',llm:true,requirementsTimeoutMs:160000})};
   if(url==='/api/requirements'){advance(55000);if(options.signal.aborted)throw options.signal.reason;return {ok:true,json:async()=>({method:'exaone',profile:'office',budget:1500000,resolution:'FHD',questions:[]})};}
   return mock(url,options);
  };w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'LaTeX로 논문을 작성할 본체 150만원');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(30);await waitFor(()=>!w.document.querySelector('.chat-send .spin'));
  assert.equal(w.document.querySelectorAll('.plan-card').length,3,'서버 처리 시간 안의 정상 응답을 기다린다');
  assert.doesNotMatch(w.document.querySelector('.chat-messages').textContent,/준비하지 못했/);
 }finally{w.close();}
});

test('UI EXAONE: 용도 확인 중 수동 사무 선택은 예산과 화이트·와이파이를 유지한다',async()=>{
 let calls=0;const state={answer:()=>({text:'',sources:[]}),requirements:()=>{calls++;return {method:'local',profile:null,needsPurpose:true,questions:['주로 어떤 용도로 쓰실 예정인가요?']};}};
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  const type=async value=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,value);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);};
  const submit=async()=>{w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(30);await waitFor(()=>!w.document.querySelector('.chat-send .spin'));};
  await type('LaTeX로 논문을 작성할 본체 150만원, 화이트 케이스와 와이파이 포함');await submit();
  assert.equal(w.document.querySelectorAll('.plan-card').length,0);
  w.document.querySelector('.options-toggle').click();await wait(30);
  [...w.document.querySelectorAll('.profile-options button')].find(b=>b.textContent==='사무·학습').click();await wait(30);
  await type('이 조건으로 견적 주세요');await submit();await waitFor(()=>w.document.querySelector('.plan-card'));
  assert.match(w.document.querySelector('.results-heading').textContent,/사무·학습.*FHD/);
  await waitFor(()=>state['/api/state/consult-demo']?.req?.needsPurpose===false);
  assert.equal(calls,1,'수동으로 용도를 정한 후에는 해석 API를 다시 호출하지 않는다');
  const req=state['/api/state/consult-demo'].req;
  assert.equal(req.profile,'office');assert.equal(req.budget,1500000);assert.equal(req.white,true);assert.equal(req.wifi,true);
 }finally{w.close();}
});

test('UI EXAONE: 명확한 용도는 직행하고 모호한 해석 요청이 실패하면 용도를 묻는다',async()=>{
 for(const [text,planCount] of [['LaTeX로 논문을 작성할 본체 150만원',0],['사무용 본체 150만원',3]]){
  const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
  const mock=apiMock(null,'demo',{answer:()=>({text:'',sources:[]})});
  try{w.fetch=(url,options)=>url==='/api/requirements'?Promise.reject(new w.DOMException('시간 초과','TimeoutError')):mock(url,options);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
   const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,text);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(30);await waitFor(()=>!w.document.querySelector('.chat-send .spin'));
   assert.equal(w.document.querySelectorAll('.plan-card').length,planCount);
   assert.equal(w.document.querySelector('.clarify'),null);if(planCount===0)assert.match(w.document.querySelector('.chat-messages').textContent,/주로 어떤 용도/);
   assert.doesNotMatch(w.document.querySelector('.chat-messages').textContent,/준비하지 못했/);
  }finally{w.close();}
 }
});

test('UI 빠른 견적: 명확한 요청과 추가 증액·무제한은 해석 API를 호출하지 않는다',async()=>{
 let calls=0;const state={answer:()=>({text:'',sources:[]}),requirements:()=>{calls++;return {method:'exaone',profile:'gaming',budget:1500000,resolution:'QHD',questions:[]};}};
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  const send=async text=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,text);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(30);await waitFor(()=>!w.document.querySelector('.chat-send .spin'));};
  await send('게임용 QHD 본체 150만원');assert.equal(calls,0);assert.equal(w.document.querySelectorAll('.plan-card').length,3);assert.match(w.document.querySelector('.interpretation').textContent,/규칙 기반/);
  await send('예산 10만원만 더 올려줘');assert.equal(calls,0);assert.match([...w.document.querySelectorAll('.chat-message.assistant')].at(-1).textContent,/1,600,000원/);
  await send('예산 제한 없이 해주세요');assert.equal(calls,0);assert.match([...w.document.querySelectorAll('.chat-message.assistant')].at(-1).textContent,/예산 제한 없음/);
 }finally{w.close();}
});

test('UI: 복원된 질문과 모델 선택 질문은 패널 없이 견적을 바로 표시한다',async()=>{
 const questions=['원하는 해상도는 무엇인가요?','Wi-Fi 내장이 필요한가요?','OS 포함이 필요한가요?'];
 const state={answer:()=>({text:'',sources:[]}),requirements:()=>({method:'exaone',profile:'office',budget:1500000,resolution:'FHD',questions}),'/api/state/consult-demo':{questions}};
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{w.fetch=apiMock(null,'demo',state);w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  assert.equal(w.document.querySelector('.clarify'),null);assert.doesNotMatch(w.document.body.textContent,/확정 전 확인해 주세요/);
  const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'LaTeX로 논문 작성할 본체 150만원');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-card'));
  assert.equal(w.document.querySelectorAll('.plan-card').length,3);assert.equal(w.document.querySelector('.clarify'),null);
  assert.doesNotMatch(w.document.body.textContent,/확정 전 확인|Wi-Fi 내장이 필요한가요|답변을 요청사항에 추가/);
 }finally{w.close();}
});

test('UI 게임 지식: 알려진 게임은 모델을 생략하고 서버가 정한 해상도와 출처를 표시한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 let modelCalls=0;
 const state={answer:()=>({}),requirements:()=>{modelCalls++;return {method:'exaone',profile:'gaming'}}};
 const fallback=apiMock(snapshot,'live',state);
 w.fetch=async(url,options={})=>{
  if(url==='/api/health')return {ok:true,json:async()=>({ok:true,mode:'live',llm:true,knowledgeGames:[{name:'Overwatch',aliases:['오버워치','OW2']}]})};
  if(url==='/api/agent/quote'){
   const {requirement:r,assembly}=JSON.parse(options.body);const settings={assembly};assert.equal(r.resolutionExplicit,false);
   const requirement={...r,resolution:'FHD',resolutionBasis:'service_default'};
   const gameEvidence={selectionNote:'원문 실측 GPU 후보 적용',limitation:'현재 견적의 FPS를 보장하지 않습니다.',games:[{id:'game:overwatch',name:'Overwatch',status:'measured_gpu_advisory',sources:[{id:'test-source',publisher:'ComputerBase',url:'https://www.computerbase.de/',accessed_at:'2026-11-11'}]}]};
   return {ok:true,json:async()=>({status:'completed',quote:{plans:buildRecommendations(requirement,settings,snapshot.parts),requirement,gameEvidence}})};
  }
  return fallback(url,options);
 };
 w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
 const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'OW2 본체');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-card'));
 assert.equal(modelCalls,0);assert.match(w.document.querySelector('.results-heading').textContent,/게임 · FHD/);
 assert.match(w.document.querySelector('.game-evidence').textContent,/FPS를 보장하지/);
 assert.match(w.document.querySelector('.game-evidence').textContent,/FHD 기본값/);
 assert.equal(w.document.querySelector('.game-evidence a').href,'https://www.computerbase.de/');
 }finally{w.close();}
});

test('UI: LLM 없이도 사이버 펑크 의문형 견적은 답변 API 대신 추천으로 간다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 let quotes=0,answers=0;const mock=apiMock(snapshot);
 w.fetch=async(url,options={})=>{
  if(url==='/api/health')return {ok:true,json:async()=>({ok:true,mode:'live',llm:false,knowledgeGames:[{name:'Cyberpunk 2077',aliases:['사이버펑크']}]})};
  if(url==='/api/answer'){answers++;throw Error('must not answer quote requests');}
  if(url==='/api/agent/quote'){quotes++;assert.equal(JSON.parse(options.body).requirement.profile,'gaming');}
  return mock(url,options);
 };
 w.eval(bundle.outputFiles[0].text);await wait(120);
 const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'사이버 펑크 견적은?');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 assert.equal(quotes,1);assert.equal(answers,0);assert.doesNotMatch(w.document.body.textContent,/제품 모델명/);
 }finally{w.close();}
});

test('UI: LLM 없이 미등록 게임을 검색하고 사무 견적에서 새 게임 용도로 전환한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 const readings=[],quotes=[];const state={requirements:({text})=>{readings.push(text);return {profile:'gaming',resolution:'FHD',method:'local',gameLookup:{status:'found',method:'steam'}};}};
 const mock=apiMock(snapshot,'live',state);w.fetch=async(url,options={})=>{if(url==='/api/agent/quote')quotes.push(JSON.parse(options.body));return mock(url,options)};
 w.eval(bundle.outputFiles[0].text);await wait(120);
 const send=async text=>{const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,text);input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));};
 await send('사무용 100만원 견적');await waitFor(()=>w.document.querySelector('.plan-price'));
 await send('Hades II 견적은?');await waitFor(()=>quotes.length===2&&/게임/.test(w.document.querySelector('.results-heading').textContent));
 assert.deepEqual(readings,['Hades II 견적은?']);assert.equal(quotes[1].requirement.profile,'gaming');assert.equal(quotes[1].requirement.budget,null);
 }finally{w.close();}
});

test('UI: LLM 없이 게임 질문을 API로 보내고 공식 출처·확인일 링크를 표시한다',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/?demo=1',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 let count=0;const state={};const mock=apiMock(null,'demo',state);
 w.fetch=async(url,options={})=>{if(url==='/api/answer'){count++;return {ok:true,json:async()=>({text:'Hades II 공식 권장 RAM 16GB. FPS 실측은 아닙니다.',sources:['web'],references:[{name:'Supergiant Games',url:'https://store.steampowered.com/app/1145350/',accessed_at:'2026-11-12'}]})};}return mock(url,options)};
 w.eval(bundle.outputFiles[0].text);await wait(120);
 const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'Hades II 게임 권장 사양은?');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.message-references a'));
 assert.equal(count,1);assert.equal(w.document.querySelector('.message-references a').href,'https://store.steampowered.com/app/1145350/');assert.match(w.document.body.textContent,/Steam 공식 스토어|2026-11-12/);assert.equal(w.document.querySelector('.results'),null);
 }finally{w.close();}
});

test('UI: 새 카탈로그 가격이 현재 부품 금액·합계에 반영되고 발행 재검증은 유지된다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date(Date.now()-60000).toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;
 try{
 let poll;const interval=w.setInterval.bind(w);w.setInterval=(fn,ms)=>{if(ms===60000){poll=fn;return 999;}return interval(fn,ms);};
 w.fetch=apiMock(snapshot);w.eval(bundle.outputFiles[0].text);await wait(120);
 const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'게임용 200만원 견적');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
 w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-price'));
 const card=()=>w.document.querySelector('.plan-card');
 const row=()=>[...card().querySelectorAll('.plan-part-row')].find(el=>el.querySelector('.plan-part-category')?.textContent.includes('그래픽'));
 const original=row().querySelector('.product-name-button').getAttribute('title');
 const record=snapshot.parts.find(p=>p.name===original);assert.ok(record);
 const oldPrice=record.price;const oldTotal=Number(card().querySelector('.plan-price').textContent.match(/[\d,]+/)[0].replaceAll(',',''));
 record.price+=9850;record.priceEvidence={...record.priceEvidence,amount:record.price,observedAt:new Date().toISOString()};snapshot.catalogVersion='new-source-price';
 await poll();await waitFor(()=>row().querySelector('.plan-part-price').textContent===new Intl.NumberFormat('ko-KR').format(oldPrice+9850)+'원');
 assert.equal(row().querySelector('.plan-part-price').textContent,new Intl.NumberFormat('ko-KR').format(oldPrice+9850)+'원');
 assert.equal(Number(card().querySelector('.plan-price').textContent.match(/[\d,]+/)[0].replaceAll(',','')),oldTotal+9850);
 assert.ok(w.document.querySelector('.regenerate-notice'),'가격 변경 후 발행 전 재검증 안내 유지');
 const issue=[...w.document.querySelectorAll('button')].find(b=>b.textContent.includes('선택안 견적서 발행'));assert.equal(issue.getAttribute('aria-disabled'),'true');
 }finally{w.close();}
});

test('UI: 예산 없는 유튜브 방송 견적은 Steam·LLM 해석 없이 생성한다',async()=>{
 const {readFileSync}=await import('node:fs');const snapshot=JSON.parse(readFileSync(new URL('../public/data/catalog.json',import.meta.url)));
 for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',runScripts:'outside-only',pretendToBeVisual:true});const w=dom.window;let requests=0;
 try{
  const mock=apiMock(snapshot,'live',{answer:()=>({})});w.fetch=(url,options={})=>{
   assert.notEqual(url,'/api/requirements');
   if(url==='/api/agent/quote'){requests++;assert.equal(JSON.parse(options.body).requirement.profile,'editing');}
   return mock(url,options);
  };w.crypto.randomUUID=()=>crypto.randomUUID();w.eval(bundle.outputFiles[0].text);await wait(150);
  const input=w.document.querySelector('#request');Object.getOwnPropertyDescriptor(w.HTMLTextAreaElement.prototype,'value').set.call(input,'유튜브 방송용 견적을 뽑아줘');input.dispatchEvent(new w.Event('input',{bubbles:true}));await wait(30);
  w.document.querySelector('.chat-composer').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await waitFor(()=>w.document.querySelector('.plan-card'));
  assert.equal(requests,1);assert.match(w.document.querySelector('.results-heading').textContent,/방송/);
 }finally{w.close();}
});
