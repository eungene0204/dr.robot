import test from 'node:test';
import assert from 'node:assert/strict';
import {knownGame,gameQuery} from '../src/game-knowledge.mjs';
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

test('게임 제목만 검색 후보로 추출하고 하드웨어·기존 견적 질문은 제외한다',async()=>{
 const {gameQuery}=await import('../src/game-knowledge.mjs');
 assert.equal(gameQuery('Hades II QHD 200만원 견적은?'),'Hades II');
 assert.equal(gameQuery('하데스 2 게임용 PC 견적 짜줘'),'하데스 2');
 for(const value of ['RTX 5060 Ti 견적은?','5060ti로 4k 게임 되나?','150만원 견적은?','이 견적으로 배그 되나?','조용한 사무용 PC'])assert.equal(gameQuery(value),null,value);
});

test('방송 제작 요청을 Steam 게임명으로 검색하지 않는다',()=>{
 for(const text of ['유튜브 방송용 견적을 뽑아줘','OBS 송출용 PC','치지직 스트리밍용 견적'])assert.equal(gameQuery(text),null);
});
