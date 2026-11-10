import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,rm} from '../backend/document-files.mjs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {expandCatalog,benchmarkName,canAdvance} from '../pipeline/expand.mjs';
import {parseSearch} from '../pipeline/adapters/danawa.mjs';
test('검색에서 키트 용량을 보존하고 같은 칩 모델의 벤치마크 이름을 연결한다',()=>{
 const html='<script type="application/ld+json">'+JSON.stringify({itemListElement:[{url:'https://prod.danawa.com/info/?pcode=123',name:'DDR5 32GB(16Gx2) 패키지'}]})+'</script><li data-product-seq="123"><a href="?pcode=123">DDR5 패키지 상세 상품</a></li>';
 assert.equal(parseSearch(html)[0].name,'DDR5 32GB(16Gx2) 패키지');
 assert.equal(benchmarkName('cpu','AMD 라이젠7-6세대 9700X (멀티팩 정품)'),'AMD Ryzen 7 9700X');
 assert.equal(benchmarkName('cpu','인텔 코어 울트라9 시리즈2 285K (애로우레이크)'),'Intel Core Ultra 9 285K');
 assert.equal(benchmarkName('gpu','MSI 지포스 RTX 5060 Ti 16GB'),'NVIDIA GeForce RTX 5060 Ti');
});
test('확장 수집은 다음 페이지에서 재개하고 일일 검색으로 신규 SKU를 발견한다',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'drrobot-expand-'));try{
 const configPath=join(dir,'discovery.json'),registryPath=join(dir,'products.json');
 await writeFile(configPath,JSON.stringify({queries:[{category:'ram',query:'DDR5'}],pagesPerPass:1,maxPagesPerQuery:3}));await writeFile(registryPath,JSON.stringify({products:[]}));
 const urls=[];const client={text:async url=>{urls.push(url);if(url.includes('search.danawa'))return {text:url.includes('sort=dateDESC')?'<li data-product-seq="124"><a href="?pcode=124">새 메모리 DDR5 32GB</a></li>':url.includes('page=1')?'<li data-product-seq="123"><a href="?pcode=123">메모리 DDR5 32GB</a></li>':'',fetchedAt:new Date().toISOString(),hash:'search'};
 return {text:'<script type="application/ld+json">'+JSON.stringify({'@type':'Product',sku:new URL(url).searchParams.get('pcode'),name:'메모리 DDR5-5600 (32GB)',description:'DDR5 / 메모리 용량: 32GB / 5600MHz',offers:{lowPrice:'100000',priceCurrency:'KRW',offerCount:3}})+'</script>',fetchedAt:new Date().toISOString(),hash:'product'};}};
 const opts={client,configPath,registryPath,dataDir:dir,onProgress:()=>{}};
 assert.equal((await expandCatalog(opts)).added,1);assert.equal((await expandCatalog(opts)).added,0);
 assert.equal(JSON.parse(await readFile(registryPath)).products.length,1);assert.ok(urls.some(url=>url.includes('page=2')));
 assert.equal((await expandCatalog({...opts,daily:true})).added,1);assert.equal(JSON.parse(await readFile(registryPath)).products.length,2);assert.ok(urls.some(url=>url.includes('sort=dateDESC')));
 }finally{await rm(dir,{recursive:true,force:true})}
});

test('두 해 수집을 위한 페이지 탐색은 임의의 100페이지에서 끝나지 않는다',()=>{assert.equal(canAdvance({page:101},{maxPagesPerQuery:null}),true);assert.equal(canAdvance({page:10001},{maxPagesPerQuery:null}),true);assert.equal(canAdvance({page:4},{maxPagesPerQuery:3}),false);assert.equal(canAdvance({page:3,done:true},{}),false)});
test('공개 카테고리의 서버 렌더링 번들 SKU도 발견한다',()=>{
 const data={productUrl:'https://prod.danawa.com/info/?pcode=123',name:'CPU 모델 멀티팩',bundleProducts:[{productCode:124,bundleName:'정품'}]};
 const frame=[1,'a:'+JSON.stringify(data)+'\n'];const html='<script>self.__next_f.push('+JSON.stringify(frame)+')</script>';
 assert.deepEqual(new Set(parseSearch(html).map(p=>p.pcode)),new Set(['123','124']));
});
