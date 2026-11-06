// OpenRouter chat completion that returns schema-checked JSON. Reasoning models spend the token budget on reasoning and return no content, so reasoning is off; providers without strict parameter support are allowed because callers validate the output.
export function createLLM({key,model,fallback,fetchImpl=fetch,onUsage=()=>{}}){
 if(!key||!model)return null;
 return async function complete({messages,schema,name,maxTokens=700,timeoutMs=30000,temperature=0}){
  const r=await fetchImpl('https://openrouter.ai/api/v1/chat/completions',{method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json','X-Title':'Dr.Robot'},body:JSON.stringify({model,...(fallback?{models:[model,fallback],route:'fallback'}:{}),reasoning:{enabled:false},messages,response_format:{type:'json_schema',json_schema:{name,strict:true,schema}},max_tokens:maxTokens,temperature}),signal:AbortSignal.timeout(timeoutMs)});
  if(!r.ok)throw new Error(`LLM 응답 오류 (${r.status})`);
  const data=await r.json();const content=data.choices?.[0]?.message?.content;
  if(!content)throw new Error('LLM 응답이 비어 있습니다.');
  onUsage({model:data.model||model,tokens:data.usage?.total_tokens||0,cost:data.usage?.cost??null});
  try{return JSON.parse(content.replace(/^```(?:json)?\s*|\s*```$/g,''))}catch{throw new Error('LLM 응답이 JSON 형식이 아닙니다.')}
 };
}
