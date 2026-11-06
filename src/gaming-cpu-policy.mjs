export function isAmdX3d(part){return part?.category==='cpu'&&/X3D(?:2)?\b/i.test(part.name||'')&&/AMD|라이젠|Ryzen/i.test(`${part.brand||''} ${part.name||''}`);}
