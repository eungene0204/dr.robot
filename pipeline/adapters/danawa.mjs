import {load} from 'cheerio';
import {SourceError} from '../http.mjs';
const number=(text,re)=>{const m=text.match(re);return m?Number(m[1].replaceAll(',','')):null;};
export function parseSpecs(category,description,name=''){
 const text=description.replace(/\s+/g,' '),spec={};
 const rawSocket=text.match(/소켓\s*(AM\d|LGA\s*\d+|\d{4})/i)?.[1]?.replaceAll(' ','');
 const socket=rawSocket&&/^\d+$/.test(rawSocket)?`LGA${rawSocket}`:rawSocket;
 const capacity=number(text,/(?:메모리 용량|용량)\s*:\s*(\d+)\s*GB/i)??number(name,/(\d+)\s*GB/i);
 if(category==='cpu')Object.assign(spec,{socket:socket||null,watts:number(text,/PBP\s*-\s*MTP\s*:\s*\d+\s*-\s*(\d+)\s*W/i)??number(text,/(?:PPT)\s*:\s*(\d+)\s*W/i)??number(text,/TDP\s*:\s*(\d+)\s*W/i),tdp:number(text,/TDP\s*:\s*(\d+)\s*W/i),igpu:/내장그래픽\s*:\s*미탑재|\/ 미탑재/.test(text)?false:/Radeon|라데온|인텔 그래픽스|내장그래픽\s*:\s*(?:탑재|Intel)/i.test(text)?true:null,cores:(()=>{const hybrid=text.match(/P\s*(\d+)\s*\+\s*E\s*(\d+)\s*코어/i);return hybrid?Number(hybrid[1])+Number(hybrid[2]):number(text,/(\d+)코어/);})(),threads:number(text,/(\d+)스레드/)});
 if(category==='board')Object.assign(spec,{socket:socket||null,ddr:number(text,/DDR\s*(\d)/i),form:/M[\s-]?ATX/i.test(text)?'mATX':/Mini[\s-]?ITX/i.test(text)?'ITX':/ATX/i.test(text)?'ATX':null,slots:number(text,/메모리 슬롯\s*:\s*(\d+)/)??number(text,/메모리\s*\/[^/]+\/\s*(\d+)개\s*\/\s*메모리 용량/),maxRam:number(text,/(?:최대 메모리|메모리 용량|최대 용량)\s*:\s*(?:최대\s*)?(\d+)\s*GB/i),m2:number(text,/M\.2\s*:\s*(\d+)개/i),wifi:/Wi-Fi|WiFi|무선랜\s*:\s*탑재/i.test(text+' '+name)?true:null,bios:null});
 if(category==='ram'){const kit=text.match(/(\d+)\s*GB\s*\(\s*(\d+)\s*G(?:B)?\s*[x×]\s*(\d+)\s*\)/i)||name.match(/(\d+)\s*GB\s*\(\s*(\d+)\s*G(?:B)?\s*[x×]\s*(\d+)\s*\)/i);Object.assign(spec,{ddr:number(text,/DDR\s*(\d)/i),capacity:kit?Number(kit[1]):capacity,sticks:kit?Number(kit[3]):/패키지|키트/.test(name)?null:1,speedMHz:number(text,/(\d{4,5})\s*MHz/i),cl:number(text,/CL\s*(\d+)/i)});}
 if(category==='gpu'){const vram=number(text,/(?:GDDR\d+[xX]?\s*\/\s*)(\d+)\s*GB/i)??number(name,/(\d+)\s*GB/i);const plug=text.match(/전원 포트\s*:\s*([^/]+)/)?.[1]||'';Object.assign(spec,{watts:number(text,/(?:사용전력|소비전력|최대 소비전력)\s*:\s*(\d+)\s*W/i),vram,length:number(text,/(?:가로\(길이\)|가로|길이)\s*:\s*(\d+(?:\.\d+)?)\s*mm/i),thickness:null,thicknessMm:number(text,/두께\s*:\s*(\d+(?:\.\d+)?)\s*mm/i),connector:/16핀/.test(plug)?'12v2x6':/8핀/.test(plug)?'8pin':null,connectorCount:number(plug,/[x×]\s*(\d+)\s*$/i),minPsu:number(text,/정격파워\s*:\s*(\d+)\s*W/i)??number(text,/(\d{3,4})\s*W\s*이상/i)});}
 if(category==='ssd'){const tb=number(name,/(\d+(?:\.\d+)?)\s*TB/i);Object.assign(spec,{capacity:tb?tb*1000:capacity,m2:/M\.2/.test(text)?1:null,readMBs:number(text,/순차읽기\s*:\s*([\d,]+)/),writeMBs:number(text,/순차쓰기\s*:\s*([\d,]+)/)});}
 if(category==='psu'){const connectors=[];if(/PCIe\s*8핀|PCIe\s*6\+2핀|PCI-E\s*6\+2핀/i.test(text))connectors.push('8pin');if(/12V[\s-]?2[x×]6/i.test(text))connectors.push('12v2x6');Object.assign(spec,{form:/SFX[ -]?L/i.test(text+' '+name)?'SFX-L':/SFX/i.test(text+' '+name)?'SFX':/TFX/i.test(text+' '+name)?'TFX':/ATX/i.test(text+' '+name)?'ATX':null,capacity:number(text,/(?:정격출력|출력)\s*:\s*(\d+)\s*W/i)??number(text,/(?:^|\/)\s*(\d{3,4})\s*W(?:\s*\/|$)/i)??number(name,/(\d{3,4})\s*W/i),connectors:connectors.length?connectors:null,efficiency:text.match(/80\s*PLUS\s*([^/]+)/i)?.[1]?.trim()||null});}
 if(category==='case'){const forms=[];if(/(?:^|[^A-Z-])ATX/i.test(text))forms.push('ATX');if(/M[\s-]?ATX/i.test(text))forms.push('mATX');if(/Mini[\s-]?ITX/i.test(text))forms.push('ITX');Object.assign(spec,{forms:forms.length?forms:null,gpuLength:number(text,/(?:VGA|GPU)(?: 장착)? (?:길이|최대길이)\s*:\s*(\d+)\s*mm/i),gpuThickness:null,expansionSlots:number(text,/(?:확장 슬롯|PCI 슬롯|PCIe 슬롯)\s*:\s*(\d+)/i),coolerHeight:number(text,/CPU\s*쿨러\s*(?:장착)?\s*높이\s*:\s*(\d+)\s*mm/i),color:/화이트|white/i.test(name)?'white':/블랙|black/i.test(name)?'black':null});}
 if(category==='cooler')Object.assign(spec,{sockets:(text.match(/AM[45]|LGA\s*\d{4}/gi)||[]).map(x=>x.replaceAll(' ','')).filter((x,i,a)=>a.indexOf(x)===i).length?(text.match(/AM[45]|LGA\s*\d{4}/gi)||[]).map(x=>x.replaceAll(' ','')):null,height:number(text,/높이\s*:\s*(\d+(?:\.\d+)?)\s*mm/i),coolingWatts:number(text,/TDP\s*:\s*(\d+)\s*W/i),color:/화이트|white/i.test(name)?'white':null});
 if(category==='os')Object.assign(spec,{included:true,licenseType:/FPP/i.test(text+' '+name)?'FPP':/DSP/i.test(text+' '+name)?'DSP':null});
 return spec;
}
export function parseProduct(html,product,meta,{allowMissingPrice=false}={}){
 const $=load(html);let data;let breadcrumbNames=[];
 for(const el of $('script[type="application/ld+json"]').toArray()){
  let value;try{value=JSON.parse($(el).text())}catch{continue}
  for(const v of Array.isArray(value)?value:[value,...(value['@graph']||[])]){if(v?.['@type']==='Product'&&String(v.sku)===String(product.danawaPcode))data=v;if(v?.['@type']==='BreadcrumbList')breadcrumbNames=(v.itemListElement||[]).map(x=>x.item?.name||x.name||'');}
 }
 if(!data||typeof data.name!=='string')throw new SourceError('상품 SKU 또는 JSON-LD 구조가 일치하지 않습니다.','schema_changed');
 const offers=Array.isArray(data.offers)?data.offers[0]:data.offers;
 const amount=Number(offers?.lowPrice??offers?.price);const offerCount=Number(offers?.offerCount);
 const hasPrice=Boolean(offers&&offers.priceCurrency==='KRW'&&Number.isSafeInteger(amount)&&amount>0&&offerCount!==0);if(!hasPrice&&!allowMissingPrice)throw new SourceError('유효한 KRW 판매가격이 없습니다.','no_price');
 const url=`https://prod.danawa.com/info/?pcode=${product.danawaPcode}`;
 const categoryNames={CPU:'cpu','메인보드':'board',RAM:'ram','그래픽카드(GPU)':'gpu',SSD:'ssd','파워':'psu','케이스':'case','쿨러/튜닝':'cooler'};const sourceCategory=breadcrumbNames.map(name=>categoryNames[name]).find(Boolean)||null;
 const specs=parseSpecs(product.category,data.description||'',data.name);
 $('script,style').remove();const listing=$('body').text().match(/등록월\s*[:：]\s*(\d{4})[.\/-]\s*(\d{1,2})/);const listingMonth=listing&&Number(listing[2])>=1&&Number(listing[2])<=12?`${listing[1]}-${listing[2].padStart(2,'0')}`:null;
 const listingDateEvidence=listingMonth?{kind:'danawa-registration-month',sourceUrl:url,observedAt:meta.fetchedAt,hash:meta.hash,precision:'month'}:null;
 return {part:{...product,name:data.name,brand:typeof data.brand==='object'?data.brand.name:data.brand,listingMonth,listingDateEvidence,sourceCategory,productType:(data.description||'').split('/')[0].trim(),...specs,specSource:{url,observedAt:meta.fetchedAt,hash:meta.hash,method:'product-jsonld',reviewed:false}},price:hasPrice?{partId:product.id,amount,currency:'KRW',shipping:null,shippingKnown:false,source:'danawa',sourceUrl:url,seller:'다나와 가격비교',sourceProductId:String(data.sku),observedAt:meta.fetchedAt,hash:meta.hash,offerCount:Number.isFinite(offerCount)?offerCount:null,availability:'listed-unconfirmed'}:null};
}
export async function collectProduct(client,product,options={}){if(!/^\d+$/.test(product.danawaPcode||''))throw new SourceError('등록된 상품 코드가 없습니다.','unmapped');const page=await client.text(`https://prod.danawa.com/info/?pcode=${product.danawaPcode}`);return parseProduct(page.text,product,page,options);}
export function parseSearch(html){
 const $=load(html);const results=new Map();
 const add=(code,name)=>{if(!/^\d+$/.test(String(code||''))||!name)return;const clean=load('<span>'+name+'</span>')('span').text().trim();if(clean.length>3&&!results.has(String(code)))results.set(String(code),{pcode:String(code),name:clean,url:`https://prod.danawa.com/info/?pcode=${code}`});};
 for(const el of $('script[type="application/ld+json"]').toArray())try{const data=JSON.parse($(el).text());if(data['@type']==='ItemList'||!data['@type'])for(const item of data.itemListElement||[])if(item.url)add(new URL(item.url).searchParams.get('pcode'),item.name)}catch{}
 for(const el of $('li[data-product-seq]').toArray()){
  const code=$(el).attr('data-product-seq');const name=$(el).find('a[href*="pcode="]').toArray().map(a=>$(a).text().trim()).find(t=>t.length>8&&!t.includes('이미지')&&!/^[\d,]+원$/.test(t));add(code,name);
 }
 for(const el of $('a[href*="pcode="]').toArray()){
  const name=$(el).text().trim();if(name.length<8||/이미지 보기|^[\d,]+원$|^의견|^상품평|가격비교 보기/.test(name))continue;
  try{const url=new URL($(el).attr('href'),'https://prod.danawa.com');if(url.hostname==='prod.danawa.com')add(url.searchParams.get('pcode'),name)}catch{}
 }
 // Read public server-rendered product/bundle data without calling restricted AJAX APIs.
 const chunks=[];for(const el of $('script').toArray()){const match=$(el).text().match(/self\.__next_f\.push\((\[[\s\S]*\])\)/);if(match)try{const frame=JSON.parse(match[1]);if(frame[0]===1&&typeof frame[1]==='string')chunks.push(frame[1])}catch{}}
 for(const line of chunks.join('').split('\n')){const body=line.slice(line.indexOf(':')+1);if(!/^[\[{]/.test(body))continue;let value;try{value=JSON.parse(body)}catch{continue}const stack=[value];let nodes=0;
  while(stack.length&&nodes++<200000){const node=stack.pop();if(!node||typeof node!=='object')continue;
   if(node.productUrl){try{const url=new URL(node.productUrl);if(url.hostname==='prod.danawa.com'){const name=node.name||node.productName;add(url.searchParams.get('pcode'),name);for(const bundle of node.bundleProducts||[])add(bundle.productCode,bundle.productName||[name,bundle.bundleName].filter(Boolean).join(' / '));}}catch{}}
   for(const child of Object.values(node))if(child&&typeof child==='object')stack.push(child);
  }
 }
 return [...results.values()];
}
