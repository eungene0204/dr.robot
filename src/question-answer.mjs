import {usablePart} from './data-policy.mjs';
// Model tokens such as 5060ti, rx9070xt, 9800x3d or i5-14400f. Bare numbers count only when they look like a 4-digit model, not a resolution or price.
const MODEL=/(rtx|gtx|rx|i[3579]-?)?\s?(\d{3,5})\s?(x3d2?|xtx|xt|gre|ti\s?super|ti|super|kf|ks|k|f|x|g)?(?![\d만원]|[,.]\d|\s?(?:만|원|p\b|hz|gb|tb|w\b))/gi;
export function modelTokens(text){
 const tokens=new Set();
 for(const m of String(text||'').toLowerCase().matchAll(MODEL)){
  const [,prefix,digits,suffix]=m;
  if(!prefix&&!suffix&&(digits.length!==4||['1080','1440','2160'].includes(digits)))continue;
  tokens.add(digits+(suffix||'').replace(/\s/g,''));
 }
 return [...tokens];
}
export function modelKey(part){
 if(!['cpu','gpu'].includes(part?.category)||part.virtual)return null;
 return modelTokens(part.benchmarkName||part.name).at(-1)??null;
}
// A question about products or capability, as opposed to a request to build a quote.
export function isQuestion(text){
 const value=String(text||'').trim();
 // A quote request asks for a build; a sentence that only mentions the current quote ("이 견적으로 배그 되나?") is still a question.
 if(/견적\s*$|(?:견적|구성|사양|pc|컴퓨터).{0,8}?(?:짜|맞춰|뽑아|만들어|내\s*줘|부탁|요청|추천)|맞춰\s*줘|구성해|짜\s*줘|추천해|뽑아\s*줘|만들어\s*줘/i.test(value))return false;
 return /\?$|？$|(?:수\s*있(?:나|나요|을까|어|습니까)|되나|되나요|될까|돌아가|가능(?:한가|할까|해|한지)|어때|어떤가|차이|뭐가|무엇|얼마|괜찮)/.test(value);
}
const money=n=>new Intl.NumberFormat('ko-KR').format(n)+'원';
const RESOLUTION=text=>/4k|2160/i.test(text)?'4K':/qhd|1440/i.test(text)?'QHD':/fhd|1080/i.test(text)?'FHD':null;
// Answers only from catalog evidence; never asserts game FPS, which the catalog does not hold.
export function answerQuestion(text,catalog,policy={}){
 const tokens=modelTokens(text);const resolution=RESOLUTION(text);const gaming=/게임|게이밍|fps|프레임|배그|롤/i.test(text)||Boolean(resolution);
 const groups=tokens.map(token=>({token,parts:catalog.filter(p=>modelKey(p)===token)})).filter(g=>g.parts.length);
 if(!groups.length)return {text:'질문에 나온 제품을 카탈로그에서 찾지 못했어요. 제품 모델명(예: RTX 5060 Ti, 9800X3D)으로 다시 물어봐 주세요.'};
 const lines=groups.map(({parts})=>{
  const sample=parts.find(p=>p.benchmarkName)||parts[0];const name=sample.benchmarkName||sample.name;
  const usable=parts.filter(p=>usablePart(p));const priced=(usable.length?usable:parts).filter(p=>Number.isFinite(p.price)&&p.price>0);
  const low=priced.length?Math.min(...priced.map(p=>p.price)):null;
  const vram=sample.category==='gpu'?[...new Set(parts.map(p=>p.vram).filter(Number.isFinite))].sort((a,b)=>a-b):[];
  const score=sample.benchmark?.normalizedScore;
  return [`${name}: 카탈로그 ${parts.length}개 제품`,vram.length?`VRAM ${vram.join('·')}GB`:null,low!==null?`최저 ${money(low)}${usable.length?'':' (가격 갱신 필요)'}`:null,Number.isFinite(score)?`Blender 렌더링 지수 ${score}`:null].filter(Boolean).join(' · ');
 });
 const notes=[];
 if(groups.some(g=>g.parts.some(p=>Number.isFinite(p.benchmark?.normalizedScore)))){const reference=policy.scoreMethod?.match(/CPU[^.]*=100[^.]*/)?.[0];notes.push(`Blender 지수는 렌더링 성능${reference?`(${reference.trim()} 기준)`:''}이며 게임 FPS가 아니에요.`);}
 if(gaming)notes.push(`${resolution?resolution+' ':''}게임 FPS 실측 자료가 없어 실행 가능 여부나 프레임을 단정할 수 없어요.`);
 return {text:[...lines,...notes].join('\n')};
}
