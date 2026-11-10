import {load} from 'cheerio';
export function parsePopularity(html,{category,sourceUrl,observedAt}){
 const $=load(html);const active=$('[role="tab"][aria-selected="true"]').toArray().some(el=>$(el).text().trim()==='인기상품순');if(!active)return [];
 const found=new Map();
 for(const el of $('.dnw-product-list .dnw-catalog-item').toArray()){
  const item=$(el);if(item.closest('.dnw-ad-item,.dnw-ad-list-item').length)continue;
  const marker=item.find('[aria-label^="인기순위 "]').first().attr('aria-label');const rank=Number(marker?.match(/^인기순위\s+(\d+)위$/)?.[1]);if(!Number.isSafeInteger(rank)||rank<1)continue;
  const representative=item.find('[data-testid="ProductListTitle"] a[href*="pcode="]').first().attr('href');let familyPcode;try{familyPcode=new URL(representative).searchParams.get('pcode')}catch{continue}
  for(const a of item.find('a[href*="pcode="]').toArray()){try{const u=new URL($(a).attr('href'));if(u.hostname!=='prod.danawa.com'||u.searchParams.get('adinflow')==='Y')continue;const pcode=u.searchParams.get('pcode');if(!/^\d+$/.test(pcode||''))continue;found.set(pcode,{pcode,popularity:{rank,category,sourceUrl,observedAt,sort:'BEST',scope:'category-family',familyPcode}});}catch{}}
 }
 return [...found.values()];
}
