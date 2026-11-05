import {readFile,writeFile,mkdir,rename,open,unlink,stat} from 'node:fs/promises';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createReadStream} from 'node:fs';
import {createHash,randomUUID} from 'node:crypto';
import {SourceClient} from './http.mjs';
import {collectProduct} from './adapters/danawa.mjs';
import {collectNaver} from './adapters/naver.mjs';
import {downloadBlender,runBlenderParser,selectBenchmarks,BLENDER_URL} from './adapters/blender.mjs';
import {PipelineStore} from './store.mjs';
import {windowCoverage} from './window.mjs';
import {hydrateSnapshot,benchmarkState,priceState,usablePart} from '../src/data-policy.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const json=async path=>JSON.parse(await readFile(path,'utf8'));
const writeJson=async(path,value)=>{await mkdir(dirname(path),{recursive:true});await writeFile(path+'.tmp',JSON.stringify(value,null,2)+'\n');await rename(path+'.tmp',path);};
export function buildSnapshot(registry,records,benchmarkRows,jobId,reviews={}){
 const byId=new Map(records.map(p=>[p.id,p]));const benchmarks=new Map(benchmarkRows.map(b=>[b.partId,b]));
 const parts=registry.products.filter(p=>p.danawaPcode||p.naverProductId).map(product=>{
  const record=byId.get(product.id);const price=record?.priceEvidence;
  const override=reviews.specOverrides?.[product.id];const validOverride=override?.reviewed===true&&/^https:\/\//.test(override?.sourceUrl||'')&&override?.reviewedAt;
  const b=benchmarks.get(product.id)||record?.benchmark||null;
  return {...product,...record,...(validOverride?override.specs:{}),id:product.id,category:product.category,name:record?.name||product.name,dataMode:'live',verified:true,virtual:false,price:price?.amount??null,observedAt:price?.observedAt??null,source:price?.source||'미수집',sourceUrl:price?.sourceUrl??null,priceEvidence:price||null,inStock:price?.availability==='out-of-stock'?false:Boolean(price),specStatus:validOverride?'reviewed':record?'parsed':'missing',specReview:validOverride?{sourceUrl:override.sourceUrl,reviewedAt:override.reviewedAt,sources:override.sources||[override.sourceUrl],notes:override.notes||null}:null,benchmark:b,score:b?.normalizedScore??null};
 });
 const virtual=[{id:'g0',category:'gpu',name:'CPU 내장 그래픽 사용',price:0,virtual:true,watts:0,vram:0,length:0,thickness:0,connector:'none',minPsu:0},{id:'o0',category:'os',name:'OS 미포함',price:0,virtual:true,included:false}].map(p=>({...p,dataMode:'live',verified:true,inStock:true,source:'선택 옵션 (실물 상품 아님)',benchmark:null}));
 const snapshot=hydrateSnapshot({schemaVersion:2,mode:'live',catalogVersion:jobId,generatedAt:new Date().toISOString(),parts:[...parts,...virtual],policy:{priceMaxAgeHours:24,benchmarkMaxAgeDays:45,benchmarkMinSamples:3,scoreLabel:'Blender 렌더링 지수',scoreMethod:'동일 버전의 monster+junkshop+classroom 합산 점수 중앙값. CPU 9600X=100 / GPU RTX 5060 Ti=100. 게임 FPS/AI 처리량 아님.',shipping:'대부분 배송비 미확인: 표시가에 미포함',stock:'가격비교에 등록된 판매 제안. 실재고 미확인'}});
 snapshot.collectionWindow=windowCoverage(snapshot.parts);
 snapshot.coverage={...snapshot.coverage,total:parts.length,freshPrices:parts.filter(p=>priceState(p)==='fresh').length,measuredBenchmarks:parts.filter(p=>benchmarkState(p)==='measured').length,benchmarkTargets:parts.filter(p=>['cpu','gpu'].includes(p.category)).length,reviewedSpecs:parts.filter(p=>p.specStatus==='reviewed').length};return snapshot;
}
export async function runPipeline(options={}){
 if(options.pricesOnly&&options.benchmarksOnly)throw new Error('가격 전용과 벤치마크 전용 옵션은 함께 지정할 수 없습니다.');
 const dataDir=resolve(options.dataDir||process.env.BUILDMATE_DATA_DIR||resolve(root,'backend/data'));await mkdir(dataDir,{recursive:true});
 const lock=resolve(dataDir,'pipeline.lock');let handle;
 try{handle=await open(lock,'wx');await handle.writeFile(JSON.stringify({pid:process.pid,at:new Date().toISOString()}));}catch(e){if(e.code!=='EEXIST')throw e;throw new Error('다른 수집 실행이 진행 중입니다. 오래된 lock은 실행 프로세스를 확인한 후 제거하세요.');}
 let store,jobId;const summary={products:0,prices:0,benchmarks:0,errors:[],quarantined:0};
 try{
  if(options.expand){const {expandCatalog}=await import('./expand.mjs');await expandCatalog({dataDir,daily:options.daily===true});}
  store=new PipelineStore(resolve(dataDir,'pipeline.db'));jobId=store.start();
  const registryPath=resolve(options.registry||resolve(root,'pipeline/config/products.json'));const registry=await json(registryPath);const {benchmarkName}=await import('./expand.mjs');let enriched=false;for(const product of registry.products){if(!product.benchmarkName){const name=benchmarkName(product.category,product.name);if(name){product.benchmarkName=name;enriched=true;}}}if(enriched)await writeJson(registryPath,registry);const reviews=await json(resolve(root,'pipeline/config/reviews.json'));
  if(!Array.isArray(registry.products)||!registry.products.length||new Set(registry.products.map(p=>p.id)).size!==registry.products.length)throw new Error('상품 레지스트리가 비어 있거나 중복되었습니다.');
  const client=options.client||new SourceClient({cacheDir:resolve(dataDir,'cache'),cacheTtlMs:options.reparseCache?24*3600000:0});
  if(!options.benchmarksOnly){for(const product of registry.products){if(!product.danawaPcode)continue;summary.products++;
   try{const observation=await collectProduct(client,product);if(store.acceptProduct(observation,reviews)){summary.prices++;if(product.naverProductId&&process.env.NAVER_CLIENT_ID){try{const cross=await collectNaver(client,product);if(Math.abs(cross.amount/observation.price.amount-1)>.3)store.queue('cross-price',product.id,'가격 소스 간 30% 이상 차이',cross.hash,{danawa:observation.price,naver:cross});}catch(e){summary.errors.push({partId:product.id,source:'naver',code:e.code||'error',message:e.message});}}}else summary.quarantined++;console.log(JSON.stringify({stage:'price',partId:product.id,name:observation.part.name,price:observation.price.amount}));}
   catch(e){summary.errors.push({partId:product.id,source:'danawa',code:e.code||'error',message:e.message});store.queue('source',product.id,e.message,e.code||e.message);console.log(JSON.stringify({stage:'error',partId:product.id,message:e.message}));}
  }}
  if(!options.pricesOnly){try{
   const archive=resolve(options.benchmarkArchive||resolve(dataDir,'blender-latest.zip'));
   if(!options.benchmarkArchive)await downloadBlender(client,archive,{force:options.refreshBenchmarks});
   const registryHash=createHash('sha256').update(JSON.stringify(registry)).digest('hex');
   const stats=await stat(archive);const parsedPath=resolve(dataDir,'blender-aggregate.json');
   let parsed;try{const info=await stat(parsedPath);if(info.mtimeMs>=stats.mtimeMs){const cached=await json(parsedPath);if(cached.registryHash===registryHash)parsed=cached;}}catch{}
   if(!parsed){console.log(JSON.stringify({stage:'benchmark',message:'공식 CC0 스냅샷 스트리밍 집계 중'}));await runBlenderParser(archive,registryPath,parsedPath);parsed=await json(parsedPath);parsed.registryHash=registryHash;await writeJson(parsedPath,parsed);}
   const hash=createHash('sha256');for await(const chunk of createReadStream(archive))hash.update(chunk);const evidenceHash=hash.digest('hex');
   // Cached snapshot keeps its original collection time; an export never refreshes evidence age.
   let meta;try{meta=await json(archive+'.meta.json')}catch{}
   const observedAt=meta?.observedAt||new Date(stats.mtimeMs).toISOString();
   const selected=selectBenchmarks(parsed.groups);const references={cpu:selected.find(b=>b.partId===(registry.benchmarkReferences?.cpu||'c2')),gpu:selected.find(b=>b.partId===(registry.benchmarkReferences?.gpu||'g2'))};
   for(const b of selected){const product=registry.products.find(p=>p.id===b.partId);if(!product)continue;const ref=references[product.category];if(!ref)continue;
    const value={...b,normalizedScore:Math.round(b.score/ref.score*1000)/10,referencePartId:ref.partId,referenceScore:ref.score,source:'Blender Open Data',sourceUrl:BLENDER_URL,license:'CC0-1.0',observedAt,evidenceHash,snapshotFile:parsed.snapshotFile};store.putBenchmark(b.partId,value);summary.benchmarks++;
   }
  }catch(e){summary.errors.push({source:'blender',message:e.message});console.log(JSON.stringify({stage:'error',source:'blender',message:e.message}));}}
  const records=store.products();const snapshot=buildSnapshot(registry,records,[],jobId,reviews);
  summary.coverage=snapshot.coverage;summary.quarantined+=store.reviews().length;
  const status=summary.errors.length||snapshot.coverage.freshPrices<snapshot.coverage.total||snapshot.coverage.measuredBenchmarks<snapshot.coverage.benchmarkTargets?'partial':'succeeded';store.finish(jobId,status,summary);
  const output=resolve(options.output||resolve(root,'public/data/catalog.json'));await writeJson(output,snapshot);
  const operational={schemaVersion:1,generatedAt:snapshot.generatedAt,jobId,status,summary,reviews:store.reviews(),jobs:store.jobs()};
  await writeJson(resolve(dataDir,'pipeline-status.json'),operational);
  // Public report excludes raw supplier payloads and private customer/store data.
  await writeJson(resolve(dirname(output),'pipeline-status.json'),{schemaVersion:1,generatedAt:operational.generatedAt,jobId,status,summary,reviews:operational.reviews});
  await writeJson(resolve(dirname(output),'price-history.json'),Object.fromEntries(registry.products.map(p=>[p.id,store.history(p.id)])));
  console.log(JSON.stringify({jobId,status,...summary,output}));return {snapshot,summary,status};
 }catch(e){if(store&&jobId)store.finish(jobId,'failed',{...summary,error:e.message});throw e;}finally{store?.close();await handle?.close();await unlink(lock);}
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2);const value=k=>{const i=args.indexOf(k);return i<0?undefined:args[i+1]};
 runPipeline({expand:args.includes('--expand'),pricesOnly:args.includes('--prices-only'),benchmarksOnly:args.includes('--benchmarks-only'),refreshBenchmarks:args.includes('--refresh-benchmarks'),reparseCache:args.includes('--reparse-cache'),benchmarkArchive:value('--benchmark-archive'),registry:value('--registry'),output:value('--output'),dataDir:value('--data-dir')}).then(({status})=>{if(status==='partial')process.exitCode=2}).catch(e=>{console.error(e.message);process.exitCode=1});
}
