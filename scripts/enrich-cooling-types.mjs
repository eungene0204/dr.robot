import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {resolve} from 'node:path';
import {storedDocument,writeFile} from '../backend/document-files.mjs';
import {parseProduct} from '../pipeline/adapters/danawa.mjs';
const snapshot=storedDocument('public/data/catalog.json');const db=new DatabaseSync('backend/data/pipeline.db');db.exec('PRAGMA busy_timeout=10000');
const counts={air:0,liquid:0,unknown:0};let changed=0;
try{for(const part of snapshot.parts.filter(p=>p.category==='cooler')){
 const url=`https://prod.danawa.com/info/?pcode=${part.danawaPcode}`;const key=createHash('sha256').update(url).digest('hex');const page=storedDocument(resolve('backend/data/cache',key+'.json'));
 let kind='unknown';try{if(page)kind=parseProduct(page.text,part,page,{allowMissingPrice:true}).part.coolingType||'unknown';}catch{}
 counts[kind]++;if(part.coolingType===kind)continue;part.coolingType=kind;part.coolingTypeEvidence={sourceUrl:url,observedAt:page?.fetchedAt||null,method:'product-jsonld'};changed++;
 const row=db.prepare('SELECT payload FROM product_facts WHERE id=?').get(part.id);if(row){const value={...JSON.parse(row.payload),coolingType:part.coolingType,coolingTypeEvidence:part.coolingTypeEvidence};db.prepare('UPDATE product_facts SET payload=? WHERE id=?').run(JSON.stringify(value),part.id);}
 }if(changed){snapshot.catalogVersion=createHash('sha256').update(JSON.stringify(snapshot.parts)).digest('hex').slice(0,20);await writeFile('public/data/catalog.json',JSON.stringify(snapshot));}console.log({changed,counts,version:snapshot.catalogVersion});}finally{db.close()}
