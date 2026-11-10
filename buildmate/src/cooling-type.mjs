export function detectCoolingType(text=''){
 const air=/공랭|air[ -]?cool(?:er|ing)?/i.test(text);
 const liquid=/수랭|수냉|liquid[ -]?cool(?:er|ing)?|water[ -]?cool(?:er|ing)?/i.test(text);
 return air===liquid?'unknown':liquid?'liquid':'air';
}
export function coolingType(part){
 if(['air','liquid','unknown'].includes(part.coolingType))return part.coolingType;
 return detectCoolingType(`${part.coolingType||''} ${part.name||''} ${part.productType||''}`);
}
