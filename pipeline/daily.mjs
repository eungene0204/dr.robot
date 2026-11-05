import {readFile,writeFile,mkdir,open,rename,unlink,stat} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {runPipeline} from './run.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
export const seoulDay=(now=new Date())=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);
const read=async(path,fallback)=>{try{return JSON.parse(await readFile(path,'utf8'))}catch(e){if(e.code==='ENOENT')return fallback;throw e}};
const save=async(path,value)=>{await writeFile(path+'.tmp',JSON.stringify(value,null,2)+'\n');await rename(path+'.tmp',path)};
const exists=async path=>{try{await stat(path);return true}catch{return false}};
export async function daily({dataDir=resolve(root,'backend/data'),run=runPipeline,now=new Date(),force=false,check=false,maxWaitMs=3*3600000,pollMs=10000}={}){
 const day=seoulDay(now),reportPath=resolve(dataDir,'daily-'+day+'.json');
 const previous=await read(reportPath,null);
 if(check)return {day,timeZone:'Asia/Seoul',schedule:'00:00',previous,waitingForCollection:await exists(resolve(dataDir,'expansion.lock'))||await exists(resolve(dataDir,'pipeline.lock'))};
 await mkdir(dataDir,{recursive:true});
 if(!force&&['succeeded','partial'].includes(previous?.status))return {day,status:'already-ran',reportPath};
 const lockPath=resolve(dataDir,'daily.lock');let lock;
 try{lock=await open(lockPath,'wx')}catch(e){
  if(e.code!=='EEXIST')throw e;
  const owner=await read(lockPath,null);if(!owner?.pid)return {day,status:'already-running'};
  try{process.kill(owner.pid,0);return {day,status:'already-running'}}catch(probe){if(probe.code!=='ESRCH')return {day,status:'already-running'}}
  await unlink(lockPath);lock=await open(lockPath,'wx');
 }
 await lock.writeFile(JSON.stringify({pid:process.pid,day,startedAt:new Date().toISOString()}));
 const started=Date.now();const report={day,timeZone:'Asia/Seoul',startedAt:new Date().toISOString(),status:'waiting'};
 try{
  await save(reportPath,report);
  // Only acquire pipeline.lock after an existing expansion/export has finished.
  while(await exists(resolve(dataDir,'pipeline.lock'))||await exists(resolve(dataDir,'expansion.lock'))){if(Date.now()-started>=maxWaitMs)throw new Error('기존 수집 대기 3시간 초과');await new Promise(r=>setTimeout(r,pollMs));}
  const before=await read(resolve(root,'pipeline/config/products.json'),{products:[]});
  report.status='running';report.beforeProducts=before.products.length;await save(reportPath,report);
  let result;
  while(!result){try{result=await run({expand:true,daily:true,dataDir})}catch(e){if((e.code==='EEXIST'||e.message.includes('다른 수집 실행'))&&Date.now()-started<maxWaitMs){await new Promise(r=>setTimeout(r,pollMs));continue}throw e;}}
  report.status=result.status;report.afterProducts=result.snapshot.parts.filter(p=>!p.virtual).length;report.addedProducts=Math.max(0,report.afterProducts-report.beforeProducts);report.coverage=result.snapshot.coverage;report.collectionWindow=result.snapshot.collectionWindow;report.errors=result.summary.errors;report.finishedAt=new Date().toISOString();await save(reportPath,report);return {...report,reportPath};
 }catch(e){report.status='failed';report.error=e.message;report.finishedAt=new Date().toISOString();await save(reportPath,report);throw e;
 }finally{await lock.close();await unlink(resolve(dataDir,'daily.lock'));}
}
if(process.argv[1]===fileURLToPath(import.meta.url))try{console.log(JSON.stringify(await daily({check:process.argv.includes('--check'),force:process.argv.includes('--force')}),null,2))}catch(e){console.error(e.message);process.exitCode=1}
