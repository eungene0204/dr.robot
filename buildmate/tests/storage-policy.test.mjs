import test from 'node:test';
import assert from 'node:assert/strict';
import {storageIssue,storageRecommendationIssue} from '../src/storage-policy.mjs';
import {usablePart} from '../src/data-policy.mjs';
import {validDiscovered} from '../pipeline/expand.mjs';
test('SSD 카테고리여도 컨버터와 용량 미확인 제품은 수집·추천에서 제외한다',()=>{for(const part of [{category:'ssd',name:'라이트컴 COMS SATA to M.2 컨버터 (KS507)',sourceCategory:'ssd',capacity:2000},{category:'ssd',name:'M.2 NVMe SSD',capacity:null},{category:'ssd',name:'NVMe USB 외장 케이스',capacity:1000}]){assert.ok(storageIssue(part));assert.equal(usablePart(part),false);assert.equal(validDiscovered(part),false)}});
test('용량이 있는 내부 SATA 및 NVMe SSD를 허용한다',()=>{for(const name of ['삼성 990 PRO NVMe M.2 (2TB)','Crucial MX500 SATA (1TB)'])assert.equal(storageIssue({category:'ssd',name,capacity:1000}),null)});

test('SATA와 인터페이스 미확인 제품은 추천에서 제외하고 NVMe만 허용한다',()=>{for(const part of [{category:'ssd',name:'PM851 M.2 SATA (128GB)',capacity:128},{category:'ssd',name:'SSD 1TB',capacity:1000},{category:'ssd',name:'SSD NVMe',interface:'SATA',capacity:1000}]){assert.ok(storageRecommendationIssue(part));assert.equal(usablePart(part),false)}assert.equal(storageRecommendationIssue({category:'ssd',name:'990 PRO NVMe 1TB',capacity:1000}),null)});
