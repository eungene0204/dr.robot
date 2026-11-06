// Re-run buildmate's (fixed) Danawa parser over its cached product pages and
// write the specs that the published snapshot is missing.
// Usage: node scripts/reparse_buildmate_specs.mjs --write data/buildmate-reparsed-specs.json
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../../buildmate',import.meta.url));
const {readFileSync,existsSync,writeFileSync}=await import('node:fs');
const {createHash}=await import('node:crypto');
const {parseSpecs}=await import(root+'/pipeline/adapters/danawa.mjs');
const {load}=await import(root+'/node_modules/cheerio/dist/esm/index.js');
const snap=JSON.parse(readFileSync(root+'/public/data/catalog.json','utf8'));
const watch={cpu:['socket','watts','tdp','igpu','cores'],board:['socket','ddr','form','slots','maxRam','m2']};
const stats={pages:0,missingCache:0,filled:{},changed:{},cleared:{}};const changedSamples=[];const updates={};
for(const p of snap.parts){
 const keys=watch[p.category];if(!keys||!p.danawaPcode)continue;
 const url=`https://prod.danawa.com/info/?pcode=${p.danawaPcode}`;
 const f=`${root}/backend/data/cache/${createHash('sha256').update(url).digest('hex')}.json`;
 if(!existsSync(f)){stats.missingCache++;continue;}
 const page=JSON.parse(readFileSync(f,'utf8'));const $=load(page.text);let data;
 for(const el of $('script[type="application/ld+json"]').toArray()){let v;try{v=JSON.parse($(el).text())}catch{continue}for(const x of Array.isArray(v)?v:[v,...(v['@graph']||[])])if(x?.['@type']==='Product'&&String(x.sku)===String(p.danawaPcode))data=x;}
 if(!data)continue;stats.pages++;
 const spec=parseSpecs(p.category,data.description||'',data.name);
 for(const k of keys){const a=p[k]??null,b=spec[k]??null;const tag=`${p.category}.${k}`;
  if(a===null&&b!==null){stats.filled[tag]=(stats.filled[tag]||0)+1;(updates[p.id]??={})[k]=b;}
  else if(a!==null&&b===null){stats.cleared[tag]=(stats.cleared[tag]||0)+1;}
  else if(a!==null&&JSON.stringify(a)!==JSON.stringify(b)){stats.changed[tag]=(stats.changed[tag]||0)+1;if(changedSamples.length<25)changedSamples.push([p.id,tag,a,b,p.name.slice(0,40)]);}}
}
console.log(JSON.stringify(stats,null,1));console.log('changed samples:');for(const s of changedSamples)console.log(' ',s.join(' | '));
const i=process.argv.indexOf('--write');if(i>0){writeFileSync(process.argv[i+1],JSON.stringify(updates));console.log('updates for',Object.keys(updates).length,'parts');}
