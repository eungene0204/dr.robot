import test from 'node:test';import assert from 'node:assert/strict';
import {coolingType,detectCoolingType} from '../src/cooling-type.mjs';
import {parseSpecs} from '../pipeline/adapters/danawa.mjs';
test('공랭과 수랭은 명시된 방식으로 분류하고 미확인은 추측하지 않는다',()=>{assert.equal(detectCoolingType('CPU 쿨러 / 공랭 / 높이: 150mm'),'air');assert.equal(parseSpecs('cooler','CPU 쿨러 / 수랭 / 라디에이터: 360mm').coolingType,'liquid');assert.equal(coolingType({name:'AG400'}),'unknown');assert.equal(coolingType({name:'수랭 호환 공랭 쿨러'}),'unknown');assert.equal(coolingType({coolingType:'air',name:'쿨러'}),'air')});
