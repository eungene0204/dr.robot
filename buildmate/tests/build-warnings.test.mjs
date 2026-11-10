import test from 'node:test';import assert from 'node:assert/strict';
import {dataIssue,warningHeading} from '../src/build-warnings.mjs';
test('가격 만료를 CPU·보드 호환성 미확인으로 표시하지 않는다',()=>{const p={category:'cpu',price:159000,priceEvidence:{sourceUrl:'https://example.org/price',observedAt:'2000-01-01'}};assert.equal(dataIssue(p),'가격 유효기간 만료');assert.equal(warningHeading([{label:'CPU 소켓',ok:true},{label:'BIOS 지원',ok:true}],[p]),'데이터 갱신 필요');assert.equal(warningHeading([{label:'BIOS 지원',ok:null}],[p]),'호환성 자료 미확인')});
