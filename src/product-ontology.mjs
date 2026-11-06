import {storageIssue} from './storage-policy.mjs';
export const ontologyVersion=2;
export const productTypes={cpu:'Processor',board:'Motherboard',ram:'MemoryModule',gpu:'GraphicsCard',ssd:'InternalDrive',psu:'PowerSupply',case:'Chassis',cooler:'CpuCooler',os:'OperatingSystem'};
export const typeParents={Processor:'PhysicalComponent',Motherboard:'PhysicalComponent',MemoryModule:'PhysicalComponent',GraphicsCard:'PhysicalComponent',InternalDrive:'StorageDevice',StorageDevice:'PhysicalComponent',StorageCache:'StorageDevice',PowerSupply:'PhysicalComponent',Chassis:'PhysicalComponent',CpuCooler:'PhysicalComponent',StorageAccessory:'Accessory',OperatingSystem:'Software',VirtualOption:'ConfigurationOption'};
export const requiredFacts={cpu:['socket','watts'],board:['socket','ddr','form','slots','maxRam'],ram:['ddr','capacity','sticks'],gpu:['vram','watts','length'],ssd:['capacity'],psu:['capacity','connectors'],case:['forms','gpuLength','coolerHeight'],cooler:['sockets','height','coolingWatts'],os:[]};
const relationFields={socket:'usesSocket',ddr:'usesMemoryGeneration',form:'hasFormFactor',forms:'acceptsFormFactor',sockets:'mountsOnSocket',connectors:'providesConnector',connector:'requiresConnector'};
export function productIssues(part){
 if(!part||!productTypes[part.category])return ['알 수 없는 제품 유형'];
 if(part.virtual)return [];
 const issues=[];const issue=storageIssue(part);if(issue)issues.push(issue);
 for(const key of requiredFacts[part.category]){
  const value=part[key];
  if(value===null||value===undefined){issues.push(`필수 속성 미확인: ${key}`);continue;}
  if(['sockets','forms','connectors'].includes(key)&&(!Array.isArray(value)||value.some(v=>typeof v!=='string')))issues.push(`속성 형식 오류: ${key}`);
  else if(['socket','form'].includes(key)&&typeof value!=='string')issues.push(`속성 형식 오류: ${key}`);
  else if(!['socket','form','sockets','forms','connectors'].includes(key)&&(!Number.isFinite(value)||value<=0))issues.push(`양수 속성 필요: ${key}`);
 }
 return [...new Set(issues)];
}
export function normalizeProduct(part){
 const issue=storageIssue(part);
 const kind=part.virtual?'VirtualOption':issue?.includes('캐시 모듈')?'StorageCache':issue?.includes('액세서리')?'StorageAccessory':productTypes[part.category]||'UnknownProduct';
 const source=part.specSource||{};
 const evidence={sourceUrl:part.specReview?.sourceUrl||source.url||null,observedAt:part.specReview?.reviewedAt||source.observedAt||null,status:part.specStatus==='reviewed'?'reviewed':source.url?'parsed':'unknown'};
 const facts=Object.entries(part).filter(([key,value])=>[...(requiredFacts[part.category]||[]),'igpu','m2','readMBs','writeMBs','thicknessMm','connector','connectorCount','minPsu','gpuLength','gpuThickness','expansionSlots','coolerHeight','form','color','wifi'].includes(key)&&value!==null&&value!==undefined&&(['string','number','boolean'].includes(typeof value)||Array.isArray(value))).map(([predicate,value])=>({predicate,value,evidence}));
 if(Number.isFinite(part.price))facts.push({predicate:'price',value:part.price,evidence:{sourceUrl:part.priceEvidence?.sourceUrl||null,observedAt:part.priceEvidence?.observedAt||null,status:part.priceEvidence?'observed':'unknown'}});
 if(Number.isFinite(part.benchmark?.normalizedScore))facts.push({predicate:'blenderNormalizedScore',value:part.benchmark.normalizedScore,evidence:{sourceUrl:part.benchmark.sourceUrl||null,observedAt:part.benchmark.observedAt||null,status:part.benchmark.sourceUrl?'observed':'unknown',version:part.benchmark.version||null}});
 if(part.popularity)facts.push({predicate:'popularityRank',value:part.popularity.rank,evidence:{...part.popularity,status:'observed'}});
 const issues=productIssues(part);
 const relations=[];
 for(const [key,predicate] of Object.entries(relationFields)){if(part[key]===null||part[key]===undefined)continue;for(const value of [].concat(part[key]))relations.push({subject:part.id,predicate,object:`${key==='socket'||key==='sockets'?'socket':key==='ddr'?'ddr':key==='form'||key==='forms'?'formFactor':key==='connector'||key==='connectors'?'connector':key}:${value}`,value,evidence});}
 // CPU support records carry their conditions; do not expand them into unconditional compatibility edges.
 for(const support of part.cpuSupport||[])relations.push({subject:part.id,predicate:'supportsProcessor',object:support.cpuId,conditions:{requiredBios:support.biosVersions||[],boardRevision:support.boardRevision||null},evidence:support.evidence||{status:'unknown'}});
 return {version:ontologyVersion,id:part.id,name:part.name,type:kind,parentType:typeParents[kind]||null,category:part.category,canFillSlot:!issues.length,status:issue?'quarantined':issues.length?'incomplete':'classified',issues,facts,relations};
}
