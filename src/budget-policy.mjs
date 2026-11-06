export const hasBudget=req=>req.budget!==null&&req.budget!==undefined;
export const validBudget=req=>!hasBudget(req)||(Number.isFinite(req.budget)&&req.budget>=200000&&req.budget<=20000000);
export const budgetLimit=(req,planId)=>hasBudget(req)?req.budget*(req.allowOver&&(planId===undefined||planId==='enhanced')?1.1:1):Infinity;
export const budgetLabel=req=>hasBudget(req)?new Intl.NumberFormat('ko-KR').format(req.budget)+'원':'예산 제한 없음';
export const unlimitedBudgetRequested=text=>/예산\s*(?:제한\s*없|상관\s*없|무관|무제한)|(?:돈|가격|비용)\s*(?:은|는|이)?\s*상관\s*없|금액\s*제한\s*없/i.test(text.split(/\n추가 요청:\s*/).at(-1));
