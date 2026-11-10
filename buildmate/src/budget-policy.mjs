export const hasBudget=req=>req.budget!==null&&req.budget!==undefined;
export const validBudget=req=>!hasBudget(req)||(Number.isFinite(req.budget)&&req.budget>=200000&&req.budget<=20000000);
export const budgetLimit=(req,planId)=>hasBudget(req)?req.budget*(req.allowOver&&(planId===undefined||planId==='enhanced')?1.1:1):Infinity;
export const budgetLabel=req=>hasBudget(req)?new Intl.NumberFormat('ko-KR').format(req.budget)+'원':'예산 제한 없음';
export const unlimitedBudgetRequested=text=>/예산\s*(?:은|는|이)?\s*(?:제한\s*없|상관\s*없|무관|무제한)|(?:돈|가격|비용)\s*(?:은|는|이)?\s*상관\s*없|금액\s*제한\s*없/i.test(text.split(/\n추가 요청:\s*/).at(-1));

export function maximumPerformanceRequested(text=''){
 const matches=[...text.matchAll(/최고\s*(?:성능|사양)|최상급|최상위|하이엔드|플래그십|끝판왕|성능\s*우선|maximum\s+performance/gi)];
 const last=matches.at(-1);return Boolean(last&&!/^[^,.\n]{0,15}(?:필요\s*없|말고|아니|원치|싫|적당|가성비)/.test(text.slice(last.index+last[0].length)));
}
