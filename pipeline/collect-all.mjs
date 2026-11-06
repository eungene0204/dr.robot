import {readFile,writeFile,rename,unlink,mkdir} from '../backend/document-files.mjs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {expandCatalog,canAdvance} from './expand.mjs';
import {runPipeline} from './run.mjs';
import {publishCatalog} from './publish.mjs';
import {acquireLock,lockHeld} from './lock.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));const dir=resolve(root,'backend/data');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
await mkdir(dir,{recursive:true});const lockPath=resolve(dir,'collection-worker.lock');let lock;try{lock=await acquireLock(lockPath)}catch(e){if(e.code==='EEXIST'){console.log('전체 수집 작업이 이미 실행 중입니다. backend/data/collection-worker.lock을 확인하세요.');process.exit(0)}throw e;}
try{
 // An already-running initial pass and its benchmark export finish first.
 while(await lockHeld(resolve(dir,'expansion.lock'))||await lockHeld(resolve(dir,'pipeline.lock')))await pause(5000);
 await pause(10000);
 while(await lockHeld(resolve(dir,'expansion.lock'))||await lockHeld(resolve(dir,'pipeline.lock')))await pause(5000);
 while(true){
  const status={running:true,pid:process.pid,at:new Date().toISOString()};const statusPath=resolve(dir,'collection-worker.json');await writeFile(statusPath+'.tmp',JSON.stringify(status));await rename(statusPath+'.tmp',statusPath);
  let lastPublished=0;
  await expandCatalog({onProgress:async message=>{console.log(message);if(Date.now()-lastPublished>15000){await publishCatalog();lastPublished=Date.now();}}});
  await runPipeline({reparseCache:true});
  const config=JSON.parse(await readFile(resolve(root,'pipeline/config/discovery.json'),'utf8'));const state=JSON.parse(await readFile(resolve(dir,'discovery-state.json'),'utf8'));
  const searching=config.queries.some(seed=>{const q=state.queries[seed.category+':'+seed.query];return !q||canAdvance(q,config);});
  if(!searching){await writeFile(statusPath,JSON.stringify({...status,running:false,finishedAt:new Date().toISOString()}));break;}
  await pause(10000);
 }
}finally{await lock.close();await unlink(lockPath);}
