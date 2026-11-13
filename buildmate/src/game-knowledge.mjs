// Match server-supplied game aliases locally; do not duplicate the knowledge dataset.
export function knownGame(text, games = []) {
 const normalize = value => value.toLowerCase().replace(/[^a-z0-9가-힣]/g, '');
 return games.some(game => !(game.excluded_aliases || []).some(alias => normalize(text).includes(normalize(alias))) && [game.name, ...game.aliases].some(alias => {
  if (/^[\x00-\x7F]+$/.test(alias)) {
   const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
   return new RegExp(`(^|[^a-z0-9])${escaped}($|[^a-z0-9])`, 'i').test(text);
  }
  const letters = alias.toLowerCase().replace(/[^a-z0-9가-힣]/g, '').split('').join('\\s*');
  return new RegExp(`(^|[^a-z0-9가-힣])${letters}($|[^a-z0-9가-힣]|용|를|을|만|도|이랑|랑|과|와|하|할|컴|견적|게임)`, 'i').test(text);
 }));
}

// Conservative title detection only; the server confirms identity and retrieves facts.
function gameQueryFragment(text) {
 const value=String(text||'').split('\n추가 요청:').at(-1).trim();
 if(/이\s*(?:견적|구성|컴퓨터)|현재\s*견적|RTX|GTX|라데온|라이젠|\bRX\s*\d|\bi[3579][ -]?\d|\d{4}\s*(?:ti|super|x3d|xt)|방송|송출|스트리밍|스트리머|\bOBS\b|streaming|streamlabs|유튜브|영상|편집|사무|개발|로컬\s*AI/i.test(value))return null;
 const end=value.search(/견적|권장\s*사양|최소\s*사양|요구\s*사양|돌아가|돌릴|실행\s*가능|게임(?:용|을|\s|$)|용\s*(?:PC|컴퓨터|본체)/i);
 if(end<0)return null;
 const title=value.slice(0,end).replace(/(?:QHD|FHD|UHD|4K|\d{3,4}p|\d+\s*(?:fps|hz|프레임)).*$/i,'').replace(/(?:예산\s*)?\d[\d,.]*\s*(?:만\s*원?|원).*$/,'').replace(/(?:\s+(?:PC|컴퓨터|본체)|용)\s*$/i,'').replace(/^[\s"'“”‘’?:,]+|[\s"'“”‘’?:,]+$/g,'');
 if(title.length<2||title.length>100||!/[a-z가-힣]/i.test(title)||/^(게임|게이밍|pc|컴퓨터|본체|추천|무제한)$/i.test(title))return null;
 return title;
}

export function gameQuery(text) {
 for(const fragment of String(text||'').split('\n추가 요청:').reverse()){const query=gameQueryFragment(fragment);if(query)return query;}
 return null;
}
