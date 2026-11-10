import {open,readFile,unlink,stat} from 'node:fs/promises';
// A process-owned lock file. A lock whose owner pid no longer exists, or an ownerless file past the write grace period, is reclaimed.
const GRACE_MS=60000;
const alive=pid=>{try{process.kill(pid,0);return true}catch(e){return e.code!=='ESRCH'}};
export async function lockHeld(path,now=Date.now()){
 let text;try{text=await readFile(path,'utf8')}catch(e){if(e.code==='ENOENT')return false;throw e}
 let owner;try{owner=JSON.parse(text)}catch{}
 if(Number.isInteger(owner?.pid))return alive(owner.pid);
 try{return now-(await stat(path)).mtimeMs<GRACE_MS}catch(e){if(e.code==='ENOENT')return false;throw e}
}
export async function acquireLock(path){
 for(let attempt=0;attempt<2;attempt++){
  try{const handle=await open(path,'wx');await handle.writeFile(JSON.stringify({pid:process.pid,at:new Date().toISOString()}));return handle;}
  catch(e){if(e.code!=='EEXIST'||attempt||await lockHeld(path))throw e;await unlink(path).catch(error=>{if(error.code!=='ENOENT')throw error});}
 }
}
