import test from 'node:test';
import assert from 'node:assert/strict';
import {knownGame} from '../src/game-knowledge.mjs';
const games=[{name:'Overwatch',aliases:['오버워치','OW2']},{name:'League of Legends',aliases:['롤','LoL']}];
test('server aliases recognize Korean particles and English boundaries without embedded-word mistakes',()=>{
 for(const text of ['오버워치용 견적','오버 워치 PC','OW2 본체','롤용','LoL'])assert.equal(knownGame(text,games),true,text);
 for(const text of ['스크롤 작업','컨트롤 프로그램','롤러코스터','ow200','unknown'])assert.equal(knownGame(text,games),false,text);
 assert.equal(knownGame('오버워치'),false);
});


test('new titles containing AI/LoRA substrings stay games; explicit other editions do not match',async()=>{
 const {detectProfile}=await import('../src/engine.mjs');
 for(const text of ['Rainbow Six Siege X','VALORANT'])assert.equal(detectProfile(text),null,text);
 for(const text of ['AI 개발','LoRA 학습','로컬AI'])assert.equal(detectProfile(text),'ai',text);
 const games=[{name:'Minecraft: Java Edition',aliases:['마크','마인크래프트','Minecraft'],excluded_aliases:['베드락','bedrock']}];
 assert.equal(knownGame('마크용 본체',games),true);
 assert.equal(knownGame('Minecraft Bedrock PC',games),false);
 assert.equal(knownGame('마인크래프트 베드락',games),false);
});
