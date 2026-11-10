import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile,writeFile} from '../backend/document-files.mjs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {daily,seoulDay} from '../pipeline/daily.mjs';
test('일일 작업 날짜는 한국 자정에서 변경된다',()=>{
 assert.equal(seoulDay(new Date('2026-11-04T14:59:59Z')),'2026-11-04');
 assert.equal(seoulDay(new Date('2026-11-04T15:00:00Z')),'2026-11-05');
});
test('일일 수집은 신규 발견을 실행하고 보고서를 남긴 후 같은 날 중복을 막는다',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'drobot-daily-'));try{
 let calls=0;const run=async options=>{assert.equal(options.expand,true);assert.equal(options.daily,true);calls++;return {status:'partial',snapshot:{parts:[{id:'one'}],coverage:{total:1}},summary:{errors:[]}}};
 const options={dataDir:dir,run,now:new Date('2026-11-04T15:00:00Z')};
 const result=await daily(options);assert.equal(result.status,'partial');assert.equal(calls,1);
 assert.equal(JSON.parse(await readFile(result.reportPath)).day,'2026-11-05');
 assert.equal((await daily(options)).status,'already-ran');assert.equal(calls,1);
 await assert.rejects(readFile(join(dir,'daily.lock')),{code:'ENOENT'});
 }finally{await rm(dir,{recursive:true,force:true})}
});
test('다른 수집과 충돌하면 기다렸다가 실행하고 실패는 보고서에 기록한다',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'drobot-daily-'));try{
 let calls=0;const run=async()=>{calls++;if(calls===1){const e=new Error('busy');e.code='EEXIST';throw e}throw new Error('source unavailable')};
 await assert.rejects(daily({dataDir:dir,run,pollMs:1,maxWaitMs:1000,now:new Date('2026-11-04T15:00:00Z')}),/source unavailable/);
 assert.equal(calls,2);assert.equal(JSON.parse(await readFile(join(dir,'daily-2026-11-05.json'))).status,'failed');
 }finally{await rm(dir,{recursive:true,force:true})}
});
