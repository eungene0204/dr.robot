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
