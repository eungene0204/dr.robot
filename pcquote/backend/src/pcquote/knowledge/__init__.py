"""Versioned, source-backed game property graph. No network or model calls at query time."""
from __future__ import annotations

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

RELATIONS = {
    'HAS_REQUIREMENT': ('game', 'requirement'), 'HAS_MEASUREMENT': ('game', 'measurement'),
    'SUPPORTED_BY': (('requirement', 'measurement'), 'source'),
    'REQUIRES_CPU': ('requirement', 'hardware'), 'REQUIRES_GPU': ('requirement', 'hardware'),
    'TESTED_CPU': ('measurement', 'hardware'), 'TESTED_GPU': ('measurement', 'hardware'),
}


def normalize(value):
    return re.sub(r'[^a-z0-9가-힣]', '', value.lower())


class GameGraph:
    def __init__(self, data):
        self.data = data
        self.nodes = {n['id']: n for n in data['nodes']}
        self.out = {}
        self.validate()
        for edge in data['edges']:
            self.out.setdefault((edge['from'], edge['relation']), []).append(self.nodes[edge['to']])

    def validate(self):
        if len(self.nodes) != len(self.data['nodes']):
            raise ValueError('Duplicate node')
        linked = set()
        edges_seen = set()
        relations_by_node = {}
        for e in self.data['edges']:
            if e['from'] not in self.nodes or e['to'] not in self.nodes:
                raise ValueError('Dangling edge')
            identity = (e['from'], e['relation'], e['to'])
            if identity in edges_seen: raise ValueError('Duplicate edge')
            edges_seen.add(identity)
            relations_by_node.setdefault(e['from'], set()).add(e['relation'])
            a, b = self.nodes[e['from']], self.nodes[e['to']]
            left, right = RELATIONS[e['relation']]
            if a['kind'] not in ((left,) if isinstance(left, str) else left) or b['kind'] != right:
                raise ValueError('Invalid relation types')
            if e['relation'] == 'SUPPORTED_BY': linked.add(a['id'])
        for n in self.nodes.values():
            if n['kind'] == 'source':
                if not n['url'].startswith('https://'): raise ValueError('Source URL required')
                date.fromisoformat(n['accessed_at']);date.fromisoformat(n['review_after'])
            if n['kind'] in ('requirement', 'measurement') and n['id'] not in linked:
                raise ValueError('Evidence without source')
            if n['kind'] == 'measurement' and not {'TESTED_CPU', 'TESTED_GPU'} <= relations_by_node.get(n['id'], set()):
                raise ValueError('Measurement hardware required')
            if n['kind'] == 'measurement' and (n['value'] <= 0 or not n.get('context') or not n.get('platform')):
                raise ValueError('Measurement context required')

    def related(self, node, relation):
        return self.out.get((node['id'], relation), [])

    def active(self, node, today):
        sources = self.related(node, 'SUPPORTED_BY')
        return bool(sources) and all(s.get('reviewed') is True and
            date.fromisoformat(s['accessed_at']) <= today <= date.fromisoformat(s['review_after']) for s in sources)

    def games(self):
        return [n for n in self.nodes.values() if n['kind'] == 'game']

    def match(self, text):
        # English short aliases need word boundaries (e.g. CS2, LoL); Korean aliases support particles.
        def matches(alias):
            if alias.isascii():
                return bool(re.search(r'(?<![a-z0-9])'+re.escape(alias)+r'(?![a-z0-9])', text, re.I))
            pattern = r'(?<![a-z0-9가-힣])' + r'\s*'.join(re.escape(c) for c in normalize(alias))
            return bool(re.search(pattern + r'(?=$|[^a-z0-9가-힣]|용|를|을|만|도|이랑|랑|과|와|하|할|컴|견적|게임)', text, re.I))
        return [g for g in self.games() if any(matches(a) for a in [g['name'], *g['aliases']])]

    def resolve(self, text, resolution='FHD', today=None):
        today = today or date.today()
        games = self.match(text)
        target = re.search(r'(\d{2,3})\s*(?:fps|프레임|hz|헤르츠)', text, re.I)
        fps = int(target[1]) if target else None
        # Unknown presets/modes are not interchangeable with the published custom settings.
        incompatible = bool(re.search(r'높음|높은|상옵|최상옵|풀옵|high|네이티브|native|낮음|낮은|최저|중간|보통|울트라|최상|에픽|경쟁|low|medium|ultra|epic|\bRT\b|레이\s*트레이싱|패스\s*트레이싱|DLSS|FSR|업스케일|생성|1%|최저\s*프레임|고정|방어|유지|안정', text, re.I))
        rows=[];allowed=None;ram=0;storage=0
        for game in games:
            official=[r for r in self.related(game,'HAS_REQUIREMENT') if self.active(r,today)]
            profile=next((r for r in official if r['tier']=='recommended'), next(iter(official),None))
            if profile:
                ram=max(ram,profile.get('ram_gb') or 0);storage=max(storage,profile.get('storage_gb') or 0)
            measurements=[m for m in self.related(game,'HAS_MEASUREMENT') if self.active(m,today)]
            # Target is a selection threshold on the reviewer's average, never a proposed-PC guarantee.
            threshold=fps or (144 if game['id']=='game:overwatch' else 60)
            applicable=[m for m in measurements if resolution=='FHD' and not incompatible and m['metric']=='average_fps'
                        and m['value']>=threshold]
            models={h['model'] for m in applicable for h in self.related(m,'TESTED_GPU')}
            allowed=models if allowed is None else allowed & models
            sources={s['id']:s for n in [*official,*measurements] for s in self.related(n,'SUPPORTED_BY')}
            rows.append({'id':game['id'],'name':game['name'],'officialProfiles':[{**r, 'cpuAlternatives':self.related(r,'REQUIRES_CPU'), 'gpuAlternatives':self.related(r,'REQUIRES_GPU')} for r in official],
                'measurements':[{**m,'gpu':self.related(m,'TESTED_GPU')[0]['label']} for m in measurements],
                'status':'measured_gpu_advisory' if models else 'coverage_gap',
                'sources':list(sources.values()),'selectionAverageFps':threshold if models else None})
        restricted=bool(games and allowed)
        return {'version':self.data['version'],'resolution':resolution,'games':rows,
                'gpuModels':sorted(allowed or []),'restrictGpu':restricted,'ramGb':ram,'storageGb':storage,
                'targetFps':fps,'fpsGuaranteed':False,
                'defaultPolicy':'해상도 미지정은 FHD, 목표 미지정은 오버워치 평균 144 / 기타 평균 60을 GPU 후보 조회 기준으로 사용합니다. 공식 요구 사양이나 보장 FPS가 아닙니다.',
                'limitation':'실측은 원문 테스트 PC(9800X3D·64GB)의 평균입니다. 현재 견적의 FPS를 보장하지 않습니다. 게임 패치·드라이버 일치도 미확인입니다. 오버워치의 프레임 생성 여부는 미확인입니다. 다른 해상도·옵션·미측정 GPU의 FPS는 환산하지 않습니다.',
                'selectionNote':'원문 FHD 사용자 설정 실측 GPU 후보를 적용했습니다.' if restricted else '요청 조건의 실측 범위가 부족하여 일반 사양 규칙을 사용합니다.'}


@lru_cache(maxsize=1)
def graph():
    return GameGraph(json.loads(Path(__file__).with_name('games.json').read_text()))
