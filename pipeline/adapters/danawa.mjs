import {load} from 'cheerio';
import {SourceError} from '../http.mjs';
const number=(text,re)=>{const m=text.match(re);return m?Number(m[1].replaceAll(',','')):null;};
export function parseSpecs(category,description,name=''){
 const text=description.replace(/\s+/g,' '),spec={};
 const socket=text.match(/소켓\s*(AM\d|LGA\s*\d+)/i)?.[1]?.replaceAll(' ','');
 const capacity=number(text,/(?:메모리 용량|용량)\s*:\s*(\d+)\s*GB/i)??number(name,/(\d+)\s*GB/i);
 if(category==='cpu')Object.assign(spec,{socket:socket||null,watts:number(text,/(?:PPT)\s*:\s*(\d+)\s*W/i)??number(text,/TDP\s*:\s*(\d+)\s*W/i),tdp:number(text,/TDP\s*:\s*(\d+)\s*W/i),igpu:/내장그래픽\s*:\s*미탑재|\/ 미탑재/.test(text)?false:/Radeon|라데온|내장그래픽\s*:\s*(?:탑재|Intel)/i.test(text)?true:null,cores:number(text,/(\d+)코어/),threads:number(text,/(\d+)스레드/)});
 if(category==='board')Object.assign(spec,{socket:socket||null,ddr:number(text,/DDR\s*(\d)/i),form:/M[\s-]?ATX/i.test(text)?'mATX':/Mini[\s-]?ITX/i.test(text)?'ITX':/ATX/i.test(text)?'ATX':null,slots:number(text,/메모리 슬롯\s*:\s*(\d+)/)??number(text,/메모리\s*\/[^/]+\/\s*(\d+)개\s*\/\s*메모리 용량/),maxRam:number(text,/(?:최대 메모리|메모리 용량|최대 용량)\s*:\s*(?:최대\s*)?(\d+)\s*GB/i),m2:number(text,/M\.2\s*:\s*(\d+)개/i),wifi:/Wi-Fi|WiFi|무선랜\s*:\s*탑재/i.test(text+' '+name)?true:null,bios:null});
 if(category==='ram'){const kit=text.match(/(\d+)\s*GB\s*\(\s*(\d+)\s*G(?:B)?\s*[x×]\s*(\d+)\s*\)/i)||name.match(/(\d+)\s*GB\s*\(\s*(\d+)\s*G(?:B)?\s*[x×]\s*(\d+)\s*\)/i);Object.assign(spec,{ddr:number(text,/DDR\s*(\d)/i),capacity:kit?Number(kit[1]):capacity,sticks:kit?Number(kit[3]):/패키지|키트/.test(name)?null:1,speedMHz:number(text,/(\d{4,5})\s*MHz/i),cl:number(text,/CL\s*(\d+)/i)});}
 if(category==='gpu'){const vram=number(text,/(?:GDDR\d+[xX]?\s*\/\s*)(\d+)\s*GB/i)??number(name,/(\d+)\s*GB/i);const plug=text.match(/전원 포트\s*:\s*([^/]+)/)?.[1]||'';Object.assign(spec,{watts:number(text,/(?:사용전력|소비전력|최대 소비전력)\s*:\s*(\d+)\s*W/i),vram,length:number(text,/(?:가로\(길이\)|가로|길이)\s*:\s*(\d+(?:\.\d+)?)\s*mm/i),thickness:null,thicknessMm:number(text,/두께\s*:\s*(\d+(?:\.\d+)?)\s*mm/i),connector:/16핀/.test(plug)?'12v2x6':/8핀/.test(plug)?'8pin':null,connectorCount:number(plug,/[x×]\s*(\d+)\s*$/i),minPsu:number(text,/정격파워\s*:\s*(\d+)\s*W/i)??number(text,/(\d{3,4})\s*W\s*이상/i)});}
 if(category==='ssd'){const tb=number(name,/(\d+(?:\.\d+)?)\s*TB/i);Object.assign(spec,{capacity:tb?tb*1000:capacity,m2:/M\.2/.test(text)?1:null,readMBs:number(text,/순차읽기\s*:\s*([\d,]+)/),writeMBs:number(text,/순차쓰기\s*:\s*([\d,]+)/)});}
 if(category==='psu'){const connectors=[];if(/PCIe\s*8핀|PCIe\s*6\+2핀|PCI-E\s*6\+2핀/i.test(text))connectors.push('8pin');if(/12V[\s-]?2[x×]6/i.test(text))connectors.push('12v2x6');Object.assign(spec,{capacity:number(text,/(?:정격출력|출력)\s*:\s*(\d+)\s*W/i)??number(text,/(?:^|\/)\s*(\d{3,4})\s*W(?:\s*\/|$)/i)??number(name,/(\d{3,4})\s*W/i),connectors:connectors.length?connectors:null,efficiency:text.match(/80\s*PLUS\s*([^/]+)/i)?.[1]?.trim()||null});}
 if(category==='case'){const forms=[];if(/(?:^|[^A-Z-])ATX/i.test(text))forms.push('ATX');if(/M[\s-]?ATX/i.test(text))forms.push('mATX');if(/Mini[\s-]?ITX/i.test(text))forms.push('ITX');Object.assign(spec,{forms:forms.length?forms:null,gpuLength:number(text,/(?:VGA|GPU)(?: 장착)? (?:길이|최대길이)\s*:\s*(\d+)\s*mm/i),gpuThickness:null,coolerHeight:number(text,/CPU\s*쿨러\s*(?:장착)?\s*높이\s*:\s*(\d+)\s*mm/i),color:/화이트|white/i.test(name)?'white':/블랙|black/i.test(name)?'black':null});}
 if(category==='cooler')Object.assign(spec,{sockets:/AM5/i.test(text)?['AM5']:null,height:number(text,/높이\s*:\s*(\d+(?:\.\d+)?)\s*mm/i),coolingWatts:number(text,/TDP\s*:\s*(\d+)\s*W/i),color:/화이트|white/i.test(name)?'white':null});
 if(category==='os')Object.assign(spec,{included:true,licenseType:/FPP/i.test(text+' '+name)?'FPP':/DSP/i.test(text+' '+name)?'DSP':null});
 return spec;
}
export function parseProduct(html,product,meta){
 const $=load(html);let data;
 for(const el of $('script[type="application/ld+json"]').toArray()){
  let value;try{value=JSON.parse($(el).text())}catch{continue}
  for(const v of Array.isArray(value)?value:[value,...(value['@graph']||[])])if(v?.['@type']==='Product'&&String(v.sku)===String(product.danawaPcode))data=v;
 }
 if(!data||typeof data.name!=='string')throw new SourceError('상품 SKU 또는 JSON-LD 구조가 일치하지 않습니다.','schema_changed');
 const offers=Array.isArray(data.offers)?data.offers[0]:data.offers;
 const amount=Number(offers?.lowPrice??offers?.price);const offerCount=Number(offers?.offerCount);
 if(!offers||offers.priceCurrency!=='KRW'||!Number.isSafeInteger(amount)||amount<=0||offerCount===0)throw new SourceError('유효한 KRW 판매가격이 없습니다.','no_price');
 const url=`https://prod.danawa.com/info/?pcode=${product.danawaPcode}`;
 const specs=parseSpecs(product.category,data.description||'',data.name);
 return {part:{...product,name:data.name,brand:typeof data.brand==='object'?data.brand.name:data.brand,...specs,specSource:{url,observedAt:meta.fetchedAt,hash:meta.hash,method:'product-jsonld',reviewed:false}},price:{partId:product.id,amount,currency:'KRW',shipping:null,shippingKnown:false,source:'danawa',sourceUrl:url,seller:'다나와 가격비교',sourceProductId:String(data.sku),observedAt:meta.fetchedAt,hash:meta.hash,offerCount:Number.isFinite(offerCount)?offerCount:null,availability:'listed-unconfirmed'}};
}
export async function collectProduct(client,product){if(!/^\d+$/.test(product.danawaPcode||''))throw new SourceError('등록된 상품 코드가 없습니다.','unmapped');const page=await client.text(`https://prod.danawa.com/info/?pcode=${product.danawaPcode}`);return parseProduct(page.text,product,page);}
export function parseSearch(html){const $=load(html);return $('li[data-product-seq]').toArray().map(el=>{const pcode=$(el).attr('data-product-seq');const name=$(el).find('a[href*="pcode="]').toArray().map(a=>$(a).text().trim()).find(t=>t.length>8&&!t.includes('이미지')&&!/^[\d,]+원$/.test(t));return name?{pcode,name,url:`https://prod.danawa.com/info/?pcode=${pcode}`}:null}).filter(Boolean);}
