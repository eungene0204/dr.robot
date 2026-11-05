import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {PipelineStore} from './store.mjs';
import {parseProduct} from './adapters/danawa.mjs';
const registry=JSON.parse(await readFile('pipeline/config/products.json','utf8'));
const store=new PipelineStore(resolve('backend/data/pipeline.db'));let updated=0,missing=0;
try{for(const product of registry.products){
 const url=`https://prod.danawa.com/info/?pcode=${product.danawaPcode}`;const key=createHash('sha256').update(url).digest('hex');
 try{const page=JSON.parse(await readFile(resolve('backend/data/cache',key+'.json'),'utf8'));const observation=parseProduct(page.text,product,page);store.updateListingDate(product.id,observation.part.listingMonth,observation.part.listingDateEvidence);updated++;}catch{missing++;}
}console.log(JSON.stringify({updated,missing,priceTimestampsChanged:false}));}finally{store.close()}
