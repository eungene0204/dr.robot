import {useCallback,useEffect,useMemo,useState} from 'react';
import {catalog as demoCatalog} from './catalog.mjs';
import {hydrateSnapshot} from './data-policy.mjs';
const fetchJson=async path=>{const r=await fetch(path,{cache:'no-store',signal:AbortSignal.timeout(8000)});if(!r.ok)throw new Error(`데이터 응답 ${r.status}`);return r.json()};
export function useCatalog(){
 const demo=new URLSearchParams(location.search).get('demo')==='1';
 const [discovery,setDiscovery]=useState(null);
 const [snapshot,setSnapshot]=useState(null);const [error,setError]=useState('');const [loading,setLoading]=useState(!demo);const [clock,setClock]=useState(Date.now());const [report,setReport]=useState(null);const [priceHistory,setPriceHistory]=useState({});const [source,setSource]=useState(null);
 const refresh=useCallback(async()=>{if(demo)return;setLoading(true);let data,active;
  for(const [url,kind]of [['/api/catalog','server'],['/data/catalog.json','snapshot']]){try{data=await fetchJson(url);hydrateSnapshot(data);active=kind;break;}catch{data=null;}}
  if(data){setSnapshot(data);setSource(active);setError('');}else setError('실제 데이터에 연결하지 못했습니다. 수집 파이프라인 상태를 확인해 주세요.');
  setLoading(false);setClock(Date.now());
  try{setReport(await fetchJson(active==='server'?'/api/pipeline/status':'/data/pipeline-status.json'));}catch{}
  try{setPriceHistory(await fetchJson('/data/price-history.json'));}catch{}
  try{setDiscovery(await fetchJson('/data/discovery-status.json'));}catch{}
 },[demo]);
 useEffect(()=>{refresh();const t=setInterval(refresh,60000);return()=>clearInterval(t)},[refresh]);
 const dataset=useMemo(()=>{if(demo)return {mode:'demo',parts:demoCatalog,coverage:{},policy:{}};if(!snapshot)return null;try{return hydrateSnapshot(snapshot,clock)}catch{return null}},[snapshot,demo,clock]);
 return {discovery,catalog:dataset?.parts||[],dataset,loading,error,refresh,report,priceHistory,source,demo};
}
export function sourcePriceLabel(part){if(part.virtual)return '선택 옵션';if(part.dataMode!=='live')return '예시 가격';if(part.priceStatus==='stale')return '기간 만료';return part.priceEvidence?.source==='danawa'?'다나와 최저가':'수집 가격';}
export const timestamp=value=>value?new Date(value).toLocaleString('ko-KR'):'미수집';
