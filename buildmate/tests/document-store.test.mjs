import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile as writeDisk,unlink,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {readFile,writeFile,rename} from '../backend/document-files.mjs';
test('JSON 이전 후 원본 없이 DB에서 복원하고 갱신한다',async()=>{const dir=await mkdtemp(join(tmpdir(),'drobot-db-'));try{const file=join(dir,'state.json');await writeDisk(file,'{"version":1}');assert.equal(JSON.parse(await readFile(file,'utf8')).version,1);await unlink(file);assert.equal(JSON.parse(await readFile(file,'utf8')).version,1);await writeFile(file+'.tmp','{"version":2}');await rename(file+'.tmp',file);assert.equal(JSON.parse(await readFile(file,'utf8')).version,2);}finally{await rm(dir,{recursive:true,force:true})}});
