// Runs buildmate's JavaScript Danawa parsers over every cached page in documents.db and writes one JSON line per page.
// Used by scripts/compare_parsers.py to check the Python port. Read-only on buildmate data.
//   node scripts/dump_js_parsers.mjs <buildmate root> <out.jsonl>
import {DatabaseSync} from 'node:sqlite';
import {createWriteStream} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const [root,out]=process.argv.slice(2);
const {parseProduct,parseSearch}=await import(pathToFileURL(resolve(root,'pipeline/adapters/danawa.mjs')));
const {parsePopularity}=await import(pathToFileURL(resolve(root,'pipeline/popularity.mjs')));
const {benchmarkName,validDiscovered}=await import(pathToFileURL(resolve(root,'pipeline/expand.mjs')));
const db=new DatabaseSync(resolve(root,'backend/data/documents.db'),{readOnly:true});
const doc=name=>JSON.parse(db.prepare('SELECT payload FROM documents WHERE path=?').get(resolve(root,name)).payload);
const registry=doc('pipeline/config/products.json'),state=doc('backend/data/discovery-state.json'),config=doc('pipeline/config/discovery.json');
const products=new Map();for(const [pcode,c] of Object.entries(state.candidates||{}))products.set(pcode,{id:'dw-'+pcode,category:c.category,name:c.name,danawaPcode:pcode});
for(const p of registry.products)if(p.danawaPcode)products.set(String(p.danawaPcode),p);
const cateCategory=new Map(config.queries.filter(q=>q.categoryCode).map(q=>[String(q.categoryCode),q.category]));
const stream=createWriteStream(out);let n=0;
for(const row of db.prepare("SELECT path,payload FROM documents WHERE path LIKE ?").iterate('%/cache/%')){
 let page;try{page=JSON.parse(row.payload)}catch{continue}
 if(typeof page.text!=='string'||typeof page.url!=='string')continue;
 const u=new URL(page.url);const rec={url:page.url,key:row.path.slice(-69,-5)};
 const run=f=>{try{return {ok:f()}}catch(e){return {error:e.message,code:e.code||null}}};
 if(u.hostname==='prod.danawa.com'&&u.pathname.startsWith('/info')){
  const product=products.get(u.searchParams.get('pcode'));if(!product)continue;rec.kind='product';rec.product=product;
  rec.result=run(()=>parseProduct(page.text,product,page,{allowMissingPrice:true}));
  if(rec.result.ok){const part=rec.result.ok.part;rec.benchmarkName=benchmarkName(part.category,part.name)??null;rec.valid=validDiscovered(part);}
 }else{
  rec.kind='search';rec.result=run(()=>parseSearch(page.text));
  if(u.pathname.startsWith('/list')){const category=cateCategory.get(u.searchParams.get('cate'))||'unknown';rec.category=category;rec.popularity=run(()=>parsePopularity(page.text,{category,sourceUrl:page.url,observedAt:page.fetchedAt}));}
 }
 if(!stream.write(JSON.stringify(rec)+'\n'))await new Promise(r=>stream.once('drain',r));
 if(++n%1000===0)console.error(n);
}
stream.end();console.error('done',n);
