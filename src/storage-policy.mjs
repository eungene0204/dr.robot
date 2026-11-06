// A storage slot requires a drive, not an accessory marketed in the SSD category.
export function storageIssue(part){
 if(part?.category!=='ssd')return null;
 const description=`${part.name||''} ${part.productType||''}`;
 if(/컨버터|변환|어댑터|아답터|adapter|converter|인클로저|enclosure|외장|external|케이블|cable|확장카드|브라켓|방열판|히트싱크|복사기|도킹|클론|케이스|USB/i.test(description))return '저장장치 액세서리 또는 외장 제품';
 if(/Optane\s*Memory|옵테인\s*메모리|캐시\s*(?:모듈|메모리)|cache\s*(?:module|memory)/i.test(description))return '주 저장장치로 사용할 수 없는 캐시 모듈';
 if(!Number.isFinite(part.capacity)||part.capacity<=0)return '저장 용량 미확인';
 return null;
}
// Recommendation preference is separate from product classification: SATA drives
// remain valid catalog products, but cannot fill a recommended storage slot.
export function storageRecommendationIssue(part){
 const issue=storageIssue(part);if(issue||part?.category!=='ssd')return issue;
 const protocol=`${part.interface||''} ${part.protocol||''} ${part.name||''} ${part.productType||''}`;
 if(/SATA|Serial\s*ATA|사타/i.test(protocol))return 'SATA 스토리지는 추천에서 제외합니다.';
 if(/U\.[23]\b|EDSFF|E[13]\.[SL]/i.test(protocol))return '별도 장착·연결 검증이 필요한 서버용 스토리지';
 if(!/NVMe/i.test(protocol))return 'NVMe 인터페이스 확인이 필요합니다.';
 return null;
}

export const minimumStorageGB=req=>req.profile==='editing'?2000:req.profile==='office'?512:req.budget==null?2000:1000;
