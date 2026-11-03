import test,{after,before} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,writeFileSync,readFileSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
const dir=mkdtempSync(join(tmpdir(),'drrobot-live-api-'));
const snapshot=JSON.parse(readFileSync('public/data/catalog.json'));
for(const p of snapshot.parts){if(p.priceEvidence)p.priceEvidence.observedAt=new Date().toISOString();if(p.benchmark)p.benchmark.observedAt=new Date().toISOString();}
const path=join(dir,'catalog.json');writeFileSync(path,JSON.stringify(snapshot));process.env.BUILDMATE_DATA_DIR=dir;process.env.CATALOG_PATH=path;process.env.DATA_MODE='live';
const {server}=await import('../backend/server.mjs');let root;
before(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));root=`http://127.0.0.1:${server.address().port}`});after(()=>new Promise(r=>server.close(()=>{rmSync(dir,{recursive:true,force:true});r()})));
const post=(path,data)=>fetch(root+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
test('실제 API: 화면과 같은 스냅샷으로 추천하며 미확인 호환성 발행을 차단한다',async()=>{const data=await(await fetch(root+'/api/catalog')).json();assert.equal(data.mode,'live');assert.ok(data.parts.find(p=>p.id==='c2').benchmark.samples>=3);const req={profile:'gaming',budget:3500000,allowOver:true,white:true};const result=await(await post('/api/recommend',{requirement:req,settings:{assembly:30000}})).json();const plan=result.plans[0];assert.ok(plan);assert.equal(plan.parts.gpu.dataMode,'live');const saved=await post('/api/quotes',{plan,req,settings:{assembly:30000},catalogVersion:data.catalogVersion});assert.equal(saved.status,422);});
test('실제 API: 가격이 만료되면 추천이 사라지며 데모로 돌아가지 않는다',async()=>{for(const p of snapshot.parts)if(p.priceEvidence)p.priceEvidence.observedAt='2000-01-01T00:00:00Z';writeFileSync(path,JSON.stringify(snapshot));const data=await(await fetch(root+'/api/catalog')).json();assert.equal(data.coverage.ready,0);const r=await(await post('/api/recommend',{requirement:{profile:'gaming',budget:3500000}})).json();assert.deepEqual(r.plans,[null,null,null]);});
