const key=demo=>`dr-consultation-session:${demo?'demo':'live'}`;
export function readConsultation(demo){
 try{
  if(new URLSearchParams(location.search).has('quote'))return null;
  const draft=JSON.parse(sessionStorage.getItem(key(demo)));
  if(draft?.schemaVersion!==1||!Array.isArray(draft.messages))return null;
  if(draft.plans&&(!draft.req||!Array.isArray(draft.plans)||draft.plans.length!==3))return null;
  return draft;
 }catch{return null;}
}
export function writeConsultation(demo,draft){
 try{
  if(new URLSearchParams(location.search).has('quote'))return;
  sessionStorage.setItem(key(demo),JSON.stringify({...draft,schemaVersion:1}));
 }catch{/* Keep the consultation usable when browser storage is unavailable. */}
}
