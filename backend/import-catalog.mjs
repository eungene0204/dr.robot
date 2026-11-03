// 허가받은 총판·거래처 데이터를 내부 표준 JSON으로 변환한 뒤 사용합니다.
import {readFileSync,writeFileSync,mkdirSync,renameSync,existsSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {categories} from '../src/catalog.mjs';
const input=process.argv[2];if(!input)throw new Error('사용법: node backend/import-catalog.mjs 거래처.json [출력.json]');
const output=resolve(process.argv[3]||'backend/data/catalog.json');
const rows=JSON.parse(readFileSync(input,'utf8'));if(!Array.isArray(rows)||!rows.length)throw new Error('부품 배열을 입력하세요.');
const previous=existsSync(output)?JSON.parse(readFileSync(output,'utf8')):[];const accepted=[],quarantine=[],ids=new Set();
const required={cpu:['socket','watts','score','igpu'],board:['socket','ddr','form','bios','slots','maxRam','m2','wifi'],ram:['ddr','capacity','sticks'],gpu:['watts','score','vram','length','thickness','connector','minPsu'],ssd:['m2','capacity'],psu:['capacity','connectors','score'],case:['forms','gpuLength','gpuThickness','coolerHeight','color'],cooler:['sockets','height','coolingWatts'],os:[]};
for(const p of rows){let reason='';if(!p.id||ids.has(p.id)||!categories.includes(p.category))reason='잘못된 ID 또는 카테고리';else if(!p.name||!Number.isFinite(p.price)||p.price<0||typeof p.inStock!=='boolean')reason='가격·재고 누락';else if(p.verified!==true||!p.sourceUrl||!/^https:\/\//.test(p.sourceUrl)||!Number.isFinite(Date.parse(p.observedAt)))reason='검수·출처·기준 시각 누락';else if(required[p.category].some(k=>p[k]===undefined||p[k]===null))reason='필수 스펙 누락';else{const old=previous.find(x=>x.id===p.id);if(old?.price>0&&Math.abs(p.price/old.price-1)>.3&&p.priceChangeApproved!==true)reason='30% 이상 가격 변동: 담당자 확인 필요';}ids.add(p.id);if(reason)quarantine.push({...p,reason});else accepted.push({...p,source:p.sourceUrl});}
mkdirSync(dirname(output),{recursive:true});
// 검수 실패 상품은 추천에서 제외. 데이터 교체는 원자적으로 수행합니다.
writeFileSync(output+'.quarantine.json',JSON.stringify(quarantine,null,2));
if(accepted.length===0)throw new Error('검수를 통과한 부품이 없습니다. 이전 정상 데이터를 유지합니다.');
writeFileSync(output+'.tmp',JSON.stringify(accepted,null,2));renameSync(output+'.tmp',output);
console.log(JSON.stringify({accepted:accepted.length,quarantined:quarantine.length,output}));
