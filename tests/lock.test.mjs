import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,writeFile,readFile,utimes} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {acquireLock,lockHeld} from '../pipeline/lock.mjs';
test('lock은 소유 pid를 기록하고 살아 있는 소유자의 lock은 빼앗지 않는다',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'drobot-lock-'));try{
 const path=join(dir,'expansion.lock');const handle=await acquireLock(path);
 assert.equal(JSON.parse(await readFile(path,'utf8')).pid,process.pid);assert.equal(await lockHeld(path),true);
 await assert.rejects(acquireLock(path),{code:'EEXIST'});await handle.close();
 }finally{await rm(dir,{recursive:true,force:true})}
});
test('종료된 프로세스나 소유자 없는 오래된 lock은 회수한다',async()=>{
 const dir=await mkdtemp(join(tmpdir(),'drobot-lock-'));try{
 const dead=join(dir,'pipeline.lock');await writeFile(dead,JSON.stringify({pid:2147483646}));
 assert.equal(await lockHeld(dead),false);await (await acquireLock(dead)).close();
 const empty=join(dir,'expansion.lock');await writeFile(empty,'');
 assert.equal(await lockHeld(empty),true,'작성 직후의 빈 lock은 유지');
 const old=new Date(Date.now()-3600000);await utimes(empty,old,old);
 assert.equal(await lockHeld(empty),false);await (await acquireLock(empty)).close();
 }finally{await rm(dir,{recursive:true,force:true})}
});
