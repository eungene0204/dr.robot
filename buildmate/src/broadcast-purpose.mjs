// Producing a live stream differs from watching one.
export const broadcastPurpose=value=>/(?:송출|\bOBS\b|스트림랩스|streamlabs)/i.test(value)||(/방송|스트리밍|스트리머|streaming/i.test(value)&&!/시청|감상|보기|보는|볼\s*용/i.test(value));
