import {SourceError} from '../http.mjs';
// Explicit productId pinning prevents RAM kit/VRAM/used-item mismatches.
export async function collectNaver(client,product,env=process.env){
 if(!env.NAVER_CLIENT_ID||!env.NAVER_CLIENT_SECRET)throw new SourceError('네이버 API 키가 설정되지 않았습니다.','missing_credentials');
 if(!product.naverProductId||!product.naverQuery)throw new SourceError('검수된 네이버 상품 매핑이 없습니다.','unmapped');
 const url=new URL('https://openapi.naver.com/v1/search/shop.json');url.search=new URLSearchParams({query:product.naverQuery,display:'100',sort:'sim',exclude:'used:rental:cbshop'});
 const page=await client.text(url.href,{api:true,headers:{'X-Naver-Client-Id':env.NAVER_CLIENT_ID,'X-Naver-Client-Secret':env.NAVER_CLIENT_SECRET}});
 const json=JSON.parse(page.text);const row=json.items?.find(p=>String(p.productId)===String(product.naverProductId)&&['1','2','3'].includes(String(p.productType)));
 if(!row||!Number.isSafeInteger(Number(row.lprice))||Number(row.lprice)<=0)throw new SourceError('매핑된 새상품의 유효 가격이 없습니다.','no_price');
 return {partId:product.id,amount:Number(row.lprice),currency:'KRW',shipping:null,shippingKnown:false,source:'naver',sourceUrl:row.link,seller:row.mallName,sourceProductId:String(row.productId),observedAt:page.fetchedAt,hash:page.hash,availability:'listed-unconfirmed'};
}
