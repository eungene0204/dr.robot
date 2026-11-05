import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {daily,seoulDay} from './daily.mjs';
const expandedRun=()=>daily();
const root=fileURLToPath(new URL('../',import.meta.url));
const stateDir=resolve(process.env.BUILDMATE_DATA_DIR||resolve(root,'backend/data'));const statePath=resolve(stateDir,'schedule-state.json');
export function scheduleSlot(now=new Date()){return `${seoulDay(now)}-00`;}
export async function startScheduler({signal,run=expandedRun,intervalMs=30000}={}){
 await mkdir(stateDir,{recursive:true});let state={};try{state=JSON.parse(await readFile(statePath,'utf8'))}catch{}
 console.log('Dr.Robot pipeline scheduler: Asia/Seoul 00:00; startup catch-up enabled');
 while(!signal?.aborted){const now=Date.now(),slot=scheduleSlot();
  const attempts=state.slot===slot?state.attempts||0:0;
  if((state.slot!==slot||state.status==='failed')&&attempts<3&&(!state.at||now-state.at>=15*60000||state.slot!==slot)){
   let status='failed';try{const result=await run();status=['succeeded','partial','already-ran','already-running'].includes(result.status)?'succeeded':'failed';}catch(e){console.error(JSON.stringify({event:'scheduled_pipeline_failed',message:e.message}));}
   state={slot,status,attempts:attempts+1,at:Date.now()};await writeFile(statePath+'.tmp',JSON.stringify(state));await rename(statePath+'.tmp',statePath);
  }
  await new Promise(resolve=>{const timer=setTimeout(done,intervalMs);function done(){clearTimeout(timer);signal?.removeEventListener('abort',done);resolve()}signal?.addEventListener('abort',done,{once:true});if(signal?.aborted)done();});
 }
}
if(process.argv[1]===fileURLToPath(import.meta.url)){const controller=new AbortController();process.once('SIGINT',()=>controller.abort());process.once('SIGTERM',()=>controller.abort());await startScheduler({signal:controller.signal});}
