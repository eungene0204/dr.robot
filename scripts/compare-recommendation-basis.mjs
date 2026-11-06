import {readFile,writeFile} from 'node:fs/promises';
import {storedDocument} from '../backend/document-files.mjs';
import {hydrateSnapshot,priceState,benchmarkState,usablePart} from '../src/data-policy.mjs';
import {normalizeProduct,productIssues} from '../src/product-ontology.mjs';
import {recommend,parseRequirement} from '../src/engine.mjs';
const raw=storedDocument(new URL('../public/data/catalog.json',import.meta.url).pathname)||JSON.parse(await readFile(new URL('../public/data/catalog.json',import.meta.url),'utf8'));
const snapshot=hydrateSnapshot(raw);const real=snapshot.parts.filter(p=>!p.virtual);
// This is an eligibility comparison, not a controlled recommendation-quality A/B test.
const baseline=p=>priceState(p)==='fresh'&&p.inStock!==false&&(!['cpu','gpu'].includes(p.category)||benchmarkState(p)==='measured');
const groups={};for(const part of real){const kind=normalizeProduct(part).type;groups[kind]??={total:0,priceAndBlenderEligible:0,graphEligible:0};groups[kind].total++;if(baseline(part))groups[kind].priceAndBlenderEligible++;if(usablePart(part))groups[kind].graphEligible++;}
const rejected=real.filter(p=>baseline(p)&&productIssues(p).length);
const conditions=[['게임 350만원 QHD',{profile:'gaming',budget:3500000,resolution:'QHD'}],['영상 편집 350만원 4K',{profile:'editing',budget:3500000,resolution:'4K'}],['로컬 AI 350만원 QHD',{profile:'ai',budget:3500000,resolution:'QHD'}],['사무 100만원 FHD',{profile:'office',budget:1000000,resolution:'FHD'}]];
const results=[];for(const [text,options]of conditions){const req=parseRequirement(text,options);const start=performance.now();const plans=recommend(req,{assembly:30000},snapshot.parts);results.push({condition:text,elapsedMs:Math.round(performance.now()-start),plans:plans.map(p=>p?{id:p.id,total:p.total,performance:p.performance,basis:p.performanceBasis.kind,cpu:p.parts.cpu.name,gpu:p.parts.gpu.name,storage:p.parts.ssd.name,checks:p.checks.length,allChecksPass:p.checks.every(c=>c.ok===true),method:p.selection.method}:null)});}
const report={at:new Date().toISOString(),catalogVersion:snapshot.catalogVersion,total:real.length,priceFresh:snapshot.coverage.freshPrices,groups,priceAndBlenderEligible:real.filter(baseline).length,graphEligible:real.filter(p=>usablePart(p)).length,rejectedByProductRules:rejected.length,converter:real.filter(p=>/KS507/.test(p.name)).map(p=>({id:p.id,name:p.name,priceAndBlenderEligible:baseline(p),graphEligible:usablePart(p),issues:productIssues(p)})),results};
await writeFile(new URL('../reports/graph-blender-comparison.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
