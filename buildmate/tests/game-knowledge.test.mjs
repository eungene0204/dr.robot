import test from 'node:test';
import assert from 'node:assert/strict';
import {knownGame} from '../src/game-knowledge.mjs';
const games=[{name:'Overwatch',aliases:['오버워치','OW2']},{name:'League of Legends',aliases:['롤','LoL']}];
test('server aliases recognize Korean particles and English boundaries without embedded-word mistakes',()=>{
 for(const text of ['오버워치용 견적','오버 워치 PC','OW2 본체','롤용','LoL'])assert.equal(knownGame(text,games),true,text);
 for(const text of ['스크롤 작업','컨트롤 프로그램','롤러코스터','ow200','unknown'])assert.equal(knownGame(text,games),false,text);
 assert.equal(knownGame('오버워치'),false);
});
