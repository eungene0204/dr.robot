"""Local game knowledge first; bounded, key-free Steam Store lookup for unknown titles.

Online records are temporary publisher listings, not reviewed graph facts or FPS
measurements. Only title queries go to Steam; store text is never model instructions.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
import re
from threading import RLock
import time

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from .knowledge import graph, normalize

LIMITATION = '공식 요구 사양은 FPS 실측이 아닙니다. CPU·GPU의 성능 동등성이나 현재 견적의 FPS를 보장하지 않습니다.'


def _game_query_fragment(text: str) -> str | None:
    """Extract a single title conservatively, without sending budgets/history to search."""
    value = text.split('\n추가 요청:')[-1].strip()
    if re.search(r'이\s*(?:견적|구성|컴퓨터)|현재\s*견적|RTX|GTX|라데온|라이젠|\bRX\s*\d|\bi[3579][ -]?\d|\d{4}\s*(?:ti|super|x3d|xt)|방송|송출|스트리밍|스트리머|\bOBS\b|streaming|streamlabs|유튜브|영상|편집|사무|개발|로컬\s*AI', value, re.I):
        return None
    end = re.search(r'견적|권장\s*사양|최소\s*사양|요구\s*사양|돌아가|돌릴|실행\s*가능|게임(?:용|을|\s|$)|용\s*(?:PC|컴퓨터|본체)', value, re.I)
    if not end:
        return None
    title = value[:end.start()]
    title = re.sub(r'(?:QHD|FHD|UHD|4K|\d{3,4}p|\d+\s*(?:fps|hz|프레임)).*$', '', title, flags=re.I)
    title = re.sub(r'(?:예산\s*)?\d[\d,.]*\s*(?:만\s*원?|원).*$', '', title)
    title = re.sub(r'(?:\s+(?:PC|컴퓨터|본체)|용)\s*$', '', title, flags=re.I).strip(' \t\n"\'“”‘’?:,')
    if not 2 <= len(title) <= 100 or normalize(title) in {'게임', '게이밍', 'pc', '컴퓨터', '본체', '추천', '무제한'}:
        return None
    if not re.search(r'[a-z가-힣]', title, re.I):
        return None
    return title


def game_query(text: str) -> str | None:
    # A budget-only follow-up retains the original game's official floors.
    for fragment in reversed(text.split('\n추가 요청:')):
        query = _game_query_fragment(fragment)
        if query:
            return query
    return None


def _profile(html: str, tier: str, appid: int) -> dict | None:
    if not isinstance(html, str) or not html.strip():
        return None
    tree = HTMLParser(html)
    for node in tree.css('script,style'):
        node.decompose()
    rows = [node.text(separator=' ', strip=True) for node in tree.css('li')]
    if not rows:
        rows = [tree.text(separator=' ', strip=True)]
    text = '\n'.join(rows)
    if not text.strip():
        return None
    def gb(label):
        # Extract only a labeled capacity. Other numbers (VRAM, OS, CPU model) are not memory.
        m = re.search(r'(?:' + label + r')\s*:\s*(\d+(?:\.\d+)?)\s*(GB|MB|TB)\b', text, re.I)
        if not m:
            return None
        return math.ceil(float(m[1]) * {'GB': 1, 'MB': .001, 'TB': 1000}[m[2].upper()])
    return {'id': f'steam:{appid}:{tier}', 'tier': tier, 'raw': text[:6000],
            'ram_gb': gb('Memory|메모리'), 'storage_gb': gb(r'Storage|저장\s*공간')}


class SteamGames:
    def __init__(self, client=None, clock=time.monotonic):
        self.client = client or httpx.Client(timeout=httpx.Timeout(5), follow_redirects=False,
                                           headers={'User-Agent': 'DrRobot/0.1 (game requirements lookup)'})
        self.clock = clock
        self.cache = {}
        self.lock = RLock()

    def cached(self, text):
        query = game_query(text)
        with self.lock:
            entry = self.cache.get(normalize(query)) if query else None
            return deepcopy(entry[1]) if entry and entry[0] > self.clock() else None

    def lookup(self, text, resolution='FHD'):
        if graph().match(text):
            return {'status': 'found', 'method': 'local', 'evidence': graph().resolve(text, resolution)}
        query = game_query(text)
        if not query:
            return None
        cached = self.cached(text)
        if cached:
            if cached.get('evidence'):
                cached['evidence']['resolution'] = resolution
            return cached
        try:
            result = self._search(query)
        except (httpx.HTTPError, ValueError, TypeError, KeyError, AttributeError, OverflowError):
            result = {'status': 'unavailable', 'query': query, 'method': 'steam',
                      'message': 'Steam 검색에 연결하지 못했어요. 잠시 후 다시 요청해 주세요.'}
        with self.lock:
            # Bounded, positive one-hour cache; failures expire quickly and never use stale specs.
            now = self.clock()
            self.cache = {k: v for k, v in self.cache.items() if v[0] > now}
            if len(self.cache) >= 256:
                self.cache.pop(next(iter(self.cache)))
            self.cache[normalize(query)] = (now + (3600 if result['status'] == 'found' else 30), deepcopy(result))
        if result.get('evidence'):
            result['evidence']['resolution'] = resolution
        return result

    def _json(self, path, **params):
        response = self.client.get('https://store.steampowered.com' + path, params=params)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError('Oversized Steam response')
        return response.json()

    def _search(self, query):
        payload = self._json('/api/storesearch/', term=query, l='koreana', cc='KR')
        items = payload.get('items') or []
        candidates = [{'id': int(item['id']), 'name': item['name'],
                       'url': f"https://store.steampowered.com/app/{int(item['id'])}/"}
                      for item in items[:8] if isinstance(item.get('name'), str) and str(item.get('id', '')).isdigit()]
        exact = [c for c in candidates if normalize(c['name']) == normalize(query)]
        base = {'query': query, 'method': 'steam'}
        if len(exact) != 1:
            return {**base, 'status': 'ambiguous' if candidates else 'not_found', 'candidates': candidates[:5],
                    'message': '검색된 게임 중 정확한 제목을 입력해 주세요.' if candidates else
                               'Steam에서 게임을 찾지 못했어요. 정확한 게임명이나 영문 제목으로 다시 알려주세요. Steam에 없는 게임일 수도 있어요.'}
        candidate = exact[0]
        appid = candidate['id']
        response = self._json('/api/appdetails', appids=appid, l='english', cc='KR')
        app = response.get(str(appid)) or {}
        data = app.get('data') or {}
        if not app.get('success') or data.get('type') != 'game' or not (data.get('platforms') or {}).get('windows'):
            return {**base, 'status': 'unsupported', 'message': 'Windows PC용 본편 게임인지 확인하지 못했어요. 정확한 본편 제목을 알려주세요.'}
        requirements = data.get('pc_requirements') or {}
        profiles = [p for tier in ('minimum', 'recommended')
                    if (p := _profile(requirements.get(tier), tier, appid))]
        if not profiles:
            return {**base, 'status': 'no_requirements', 'candidates': [candidate],
                    'message': f"{candidate['name']}의 공식 Windows 요구 사양이 공개되지 않았어요. 사양을 추측해 게임용 견적을 확정할 수 없어요."}
        today = datetime.now(timezone.utc).date().isoformat()
        source = {'id': f'steam:{appid}', 'url': candidate['url'], 'publisher': ', '.join(data.get('publishers') or ['Steam']),
                  'accessed_at': today, 'reviewed': False, 'origin': 'steam_live'}
        recommended = next((p for p in profiles if p['tier'] == 'recommended'), profiles[0])
        evidence = {'version': 'steam-live', 'resolution': 'FHD', 'games': [{
            'id': f'steam:{appid}', 'name': data.get('name') or candidate['name'], 'officialProfiles': profiles,
            'officialProfileApplied': recommended['id'], 'measurements': [], 'applicableMeasurementIds': [],
            'status': 'official_only', 'sources': [source], 'notes': ['Steam 공식 스토어 실시간 조회 · 그래프 수동 검수 전']}],
            'ramGb': recommended.get('ram_gb') or 0, 'storageGb': max(p.get('storage_gb') or 0 for p in profiles),
            'restrictGpu': False, 'gpuModels': [], 'gpuVariants': [], 'targetFps': None, 'fpsGuaranteed': False,
            'selectionNote': 'Steam 공식 요구 사양의 RAM·설치 용량을 반영합니다. CPU·GPU는 일반 추천 기준이며 게임별 성능 검증은 필요합니다.',
            'limitation': LIMITATION}
        return {**base, 'status': 'found', 'evidence': evidence}


def game_answer(result):
    if not result:
        return None
    refs = []
    if result['status'] != 'found':
        candidates = result.get('candidates') or []
        names = ' / '.join(c['name'] for c in candidates)
        return {'text': result['message'] + (f' 후보: {names}' if names else ''),
                'sources': ['web'] if candidates else [], 'references': candidates, 'method': 'game', 'gameLookup': result}
    lines = []
    evidence = result['evidence']
    for game in evidence['games']:
        lines.append(game['name'])
        for p in game['officialProfiles']:
            label = '권장' if p['tier'].startswith('recommended') else '최소'
            if p.get('raw'):
                lines.append(f"공식 {label} 사양: {p['raw']}")
            else:
                cpu = ' / '.join(h['label'] for h in p.get('cpuAlternatives', []))
                gpu = ' / '.join(h['label'] for h in p.get('gpuAlternatives', []))
                bits = [f'CPU {cpu}' if cpu else '', f'GPU {gpu}' if gpu else '',
                        f"RAM {p['ram_gb']}GB" if p.get('ram_gb') else '',
                        f"설치 공간 {p['storage_gb']}GB" if p.get('storage_gb') else '']
                lines.append(f"공식 {label} 사양: " + ' · '.join(b for b in bits if b))
        if not game['officialProfiles']:
            lines.append('현재 유효한 공식 사양 근거가 없어 재확인이 필요해요.')
        refs.extend({'name': s['publisher'], 'url': s['url'], 'accessed_at': s['accessed_at']} for s in game['sources'])
    lines.append(LIMITATION)
    return {'text': '\n'.join(lines), 'sources': ['game' if result['method'] == 'local' else 'web'],
            'references': refs, 'method': 'game', 'gameLookup': result}


steam_games = SteamGames()
