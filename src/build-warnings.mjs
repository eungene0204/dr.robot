import {priceState,benchmarkState} from './data-policy.mjs';
import {productIssues} from './product-ontology.mjs';
import {storageRecommendationIssue} from './storage-policy.mjs';
export function dataIssue(part){
 if(priceState(part)==='stale')return '가격 유효기간 만료';
 if(priceState(part)==='missing')return '가격 자료 미수집';
 if(['cpu','gpu'].includes(part.category)&&!part.virtual&&benchmarkState(part)!=='measured')return '성능 실측 자료 누락·만료';
 const issues=productIssues(part);if(issues.length)return issues.join(', ');
 if(storageRecommendationIssue(part))return storageRecommendationIssue(part);
 if(part.inStock===false)return '판매 상태 확인 불가';
 return '사용 가능한 데이터가 아닙니다.';
}
export function warningHeading(checks,invalidParts){
 if(checks.some(c=>c.ok===false))return '호환성·구성 조건 불충족';
 if(checks.some(c=>c.ok===null))return '호환성 자료 미확인';
 return invalidParts.length?'데이터 갱신 필요':'안내';
}
