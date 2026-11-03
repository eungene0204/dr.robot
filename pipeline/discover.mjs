import {SourceClient} from './http.mjs';
import {parseSearch} from './adapters/danawa.mjs';
// Discovery deliberately does not write the trusted registry. Review the exact SKU/variant first.
const query=process.argv.slice(2).join(' ');if(!query)throw new Error('사용법: npm run pipeline:discover -- 부품 모델명');
const client=new SourceClient();const url='https://search.danawa.com/dsearch.php?query='+encodeURIComponent(query);const page=await client.text(url);console.log(JSON.stringify({query,collectedAt:page.fetchedAt,candidates:parseSearch(page.text).slice(0,20),next:'용량·키트·VRAM·유통 형태를 확인한 후 pipeline/config/products.json에 SKU를 등록하세요.'},null,2));
