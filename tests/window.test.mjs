import test from 'node:test';import assert from 'node:assert/strict';
import {collectionWindow,windowCoverage} from '../pipeline/window.mjs';
test('최근 2년 범위를 한국 날짜로 잡고 등록월과 실제 출시일을 구분한다',()=>{
 const range=collectionWindow(new Date('2026-11-04T15:00:00Z'));assert.equal(range.start,'2024-11-05');assert.equal(range.end,'2026-11-05');
 const coverage=windowCoverage([{listingMonth:'2025-01'},{listingMonth:'2024-11'},{listingMonth:'2020-01'},{listingMonth:null}],range);
 assert.equal(coverage.confirmedRelease,0);assert.equal(coverage.recentListing,1);assert.equal(coverage.boundaryListingMonth,1);assert.equal(coverage.dateUnknown,1);assert.equal(coverage.complete,false);
});
