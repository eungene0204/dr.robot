import {readFile,writeFile,rename} from '../backend/document-files.mjs';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {PipelineStore} from './store.mjs';
import {buildSnapshot} from './run.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
export async function publishCatalog(){
 const registry=JSON.parse(await readFile(resolve(root,'pipeline/config/products.json'),'utf8'));
 const reviews=JSON.parse(await readFile(resolve(root,'pipeline/config/reviews.json'),'utf8'));
 const store=new PipelineStore(resolve(root,'backend/data/pipeline.db'));
 try{
  const records=store.products();const version=createHash('sha256').update(JSON.stringify({registry,reviews,records})).digest('hex').slice(0,20);
  const snapshot=buildSnapshot(registry,records,[],version,reviews);
  const path=resolve(root,'public/data/catalog.json');await writeFile(path+'.publish.tmp',JSON.stringify(snapshot,null,2)+'\n');await rename(path+'.publish.tmp',path);
  try{const state=JSON.parse(await readFile(resolve(root,'backend/data/discovery-state.json'),'utf8'));const candidates=Object.values(state.candidates||{});const counts={};for(const p of candidates)counts[p.status]=(counts[p.status]||0)+1;const progress={updatedAt:state.updatedAt,discovered:candidates.length,collectionWindow:snapshot.collectionWindow,...counts};const path=resolve(root,'public/data/discovery-status.json');await writeFile(path+'.tmp',JSON.stringify(progress,null,2)+'\n');await rename(path+'.tmp',path);}catch{}
  console.log(JSON.stringify({stage:'published',total:snapshot.coverage.total,ready:snapshot.coverage.ready,benchmarks:snapshot.coverage.measuredBenchmarks,version}));return snapshot;
 }finally{store.close();}
}
if(process.argv[1]===fileURLToPath(import.meta.url))await publishCatalog();
