import {archiveAsset,readFile as readDocument,writeFile as writeDocument} from '../../backend/document-files.mjs';
import {mkdtemp,writeFile as writeTemporary,readFile as readTemporary,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createWriteStream} from 'node:fs';
import {stat,rename,writeFile} from 'node:fs/promises';
import {Readable,Transform} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
export const BLENDER_URL='https://opendata.blender.org/snapshots/opendata-latest.zip';
export async function downloadBlender(client,path,{force=false}={}){
 try{const info=await stat(path);if(!force&&Date.now()-info.mtimeMs<7*86400000)return {cached:true};}catch{}
 // This URL is the official downloadable CC0 data export, not an HTML crawl.
 // Keep our identified User-Agent; obey HTTP errors, rate limits and download size limits.
 // Website crawl exclusions for the snapshots directory prevent indexing, not use of the published data archive.
 const r=await client.raw(BLENDER_URL);let count=0;const hash=createHash('sha256');
 await pipeline(Readable.fromWeb(r.body),new Transform({transform(chunk,enc,next){count+=chunk.length;if(count>250_000_000)return next(new Error('벤치마크 ZIP 용량 제한'));hash.update(chunk);next(null,chunk);}}),createWriteStream(path+'.tmp'));
 await rename(path+'.tmp',path);await archiveAsset(path);await writeDocument(path+'.meta.json',JSON.stringify({sourceUrl:BLENDER_URL,hash:hash.digest('hex'),observedAt:new Date().toISOString(),lastModified:r.headers.get('last-modified'),bytes:count}));return {cached:false,bytes:count};
}
export async function runBlenderParser(path,registry,output){const folder=await mkdtemp(join(tmpdir(),'drobot-blender-'));const registryFile=join(folder,'registry.json');const outputFile=join(folder,'aggregate.json');await writeTemporary(registryFile,await readDocument(registry));try{const result=await new Promise((resolve,reject)=>{const child=spawn('python3',[fileURLToPath(new URL('../tools/blender.py',import.meta.url)),path,registryFile,outputFile],{stdio:['ignore','pipe','pipe']});let stdout='',stderr='';child.stdout.on('data',v=>stdout+=v);child.stderr.on('data',v=>stderr+=v);child.on('error',reject);child.on('close',code=>code===0?resolve(stdout.trim()):reject(new Error('Blender 파싱 실패: '+stderr.slice(-1000))));});await writeDocument(output,await readTemporary(outputFile));return result;}finally{await rm(folder,{recursive:true,force:true})}}
export function selectBenchmarks(groups,{minimumSamples=3}={}){
 const valid=groups.filter(r=>r.samples>=minimumSamples&&Number.isFinite(r.score)&&r.score>0&&(['CPU','OPTIX'].includes(r.backend)));
 const versions=[...new Set(valid.map(r=>r.version))];
 const coverage=v=>new Set(valid.filter(r=>r.version===v).map(r=>r.partId)).size;
 versions.sort((a,b)=>coverage(b)-coverage(a)||b.localeCompare(a,undefined,{numeric:true}));
 const version=versions[0];if(!version)return [];
 const result=[];for(const id of new Set(valid.filter(r=>r.version===version).map(r=>r.partId))){const options=valid.filter(r=>r.version===version&&r.partId===id).sort((a,b)=>b.samples-a.samples);result.push(options[0]);}
 return result;
}
