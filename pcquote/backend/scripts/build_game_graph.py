"""Build the packaged graph from the reviewed, cited research JSON blocks."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERSION = '2026-11-11.2'
REVIEW_AFTER = '2027-02-11'
REQUIREMENT_FILES = (
    '2026-11-11-game-requirements-sources.md',
    '2026-11-11-game-expansion-a.md',
    '2026-11-11-game-expansion-b.md',
)
BENCHMARK_FILE = '2026-11-11-game-benchmark-sources.md'
EXPANSION_BENCHMARK_FILE = '2026-11-11-game-expansion-benchmarks.md'


def read(name):
    contents = (ROOT / 'docs/research' / name).read_text()
    return json.loads(re.search(r'```json\s*(.*?)```', contents, re.S)[1])


def build():
    nodes, edges = {}, []

    def node(identifier, node_type, **data):
        if 'kind' in data:
            data['source_kind'] = data.pop('kind')
        record = {**data, 'id': identifier, 'kind': node_type}
        existing = nodes.get(identifier)
        if existing and existing != record:
            # Shared hardware may have additional facts in another official table.
            if node_type != 'hardware':
                raise ValueError(f'Conflicting node: {identifier}')
            for key in (existing.keys() & record.keys()) - {"label", "labels"}:
                if existing[key] != record[key]:
                    raise ValueError(f'Conflicting hardware fact: {identifier}/{key}')
            labels = sorted({existing['label'], record['label'], *existing.get('labels', [])})
            record = {**existing, **record, 'label': existing['label']}
            if len(labels) > 1:
                record['labels'] = labels
        nodes[identifier] = record
        return identifier

    def edge(start, relation, end):
        record = {'from': start, 'relation': relation, 'to': end}
        if relation.startswith('REQUIRES_'):
            record.update(operator='any', alternative_group=start + ':' + relation)
        if record not in edges:
            edges.append(record)

    def hardware(data, category):
        variant = ':vram' + str(data['vram_gb']) if data.get('vram_gb') else ''
        return node('hardware:' + data['id'] + variant, 'hardware', category=category,
                    **{k: v for k, v in data.items() if k != 'id'})

    for filename in REQUIREMENT_FILES:
        for game in read(filename)['games']:
            properties = {k: v for k, v in game.items() if k not in ('game_id', 'source', 'profiles')}
            # Common names have a default edition; explicitly different editions never match it.
            exclusions = {'minecraft_java': ['bedrock', '베드락'],
                          'gta_v_enhanced': ['legacy', '레거시', '일반판'],
                          'maplestory': ['메이플스토리 월드', '메이플스토리월드', 'maplestory worlds']}
            if game['game_id'] in exclusions:
                properties['excluded_aliases'] = exclusions[game['game_id']]
            gid = node('game:' + game['game_id'], 'game', **properties)
            sid = node('source:' + game['game_id'], 'source', **game['source'],
                       reviewed=True, review_after=REVIEW_AFTER)
            for profile in game['profiles']:
                rid = node(gid + ':' + profile['id'], 'requirement', tier=profile['id'],
                           **{k: v for k, v in profile.items()
                              if k not in ('id', 'cpu_alternatives', 'gpu_alternatives')})
                edge(gid, 'HAS_REQUIREMENT', rid)
                edge(rid, 'SUPPORTED_BY', sid)
                for category in ('cpu', 'gpu'):
                    for item in profile[category + '_alternatives']:
                        edge(rid, 'REQUIRES_' + category.upper(), hardware(item, category))

    batches = [read(BENCHMARK_FILE), *read(EXPANSION_BENCHMARK_FILE)['benchmarks']]
    for batch in batches:
        source = batch['source']
        sid = node('source:' + source['id'], 'source', url=source['methodology_url'],
                   publisher=source['owner'], accessed_at=batch['accessed_at'], reviewed=True,
                   review_after=REVIEW_AFTER, published_at=source.get('published_at'),
                   source_kind=source.get('kind'))
        for observation in batch['observations']:
            context = batch['contexts'][observation['context']]
            game_id = 'overwatch' if context['game'] == 'overwatch-2' else context['game'].replace('-', '_')
            gid = 'game:' + game_id
            if gid not in nodes:
                raise ValueError(f'Unknown measured game: {gid}')
            mid = node('measurement:' + observation['id'], 'measurement',
                       **{k: v for k, v in observation.items() if k not in ('id', 'context', 'gpu')},
                       context=context, platform=batch['platform'])
            chip = re.search(r'(?:RTX|GTX|RX)\s*(\d{4})\s*(Ti\s*SUPER|Ti|SUPER|XTX|XT)?\b',
                             observation['gpu'], re.I)
            model = (chip[1] + re.sub(r'\s', '', chip[2] or '')).lower() if chip else None
            brand = ('nvidia' if re.search(r'GeForce|RTX|GTX', observation['gpu'], re.I) else
                     'amd' if re.search(r'Radeon|RX', observation['gpu'], re.I) else None)
            gpu = hardware({'id': re.sub('[^a-z0-9]+', '-', observation['gpu'].lower()),
                            'label': observation['gpu'], 'model': model, 'brand': brand,
                            'vram_gb': observation['vram_gb']}, 'gpu')
            cpu_name = batch['platform']['cpu']
            cpu = hardware({'id': re.sub('[^a-z0-9]+', '-', cpu_name.lower()), 'label': cpu_name}, 'cpu')
            edge(gid, 'HAS_MEASUREMENT', mid)
            edge(mid, 'SUPPORTED_BY', sid)
            edge(mid, 'TESTED_GPU', gpu)
            edge(mid, 'TESTED_CPU', cpu)
    return {'version': VERSION, 'nodes': list(nodes.values()), 'edges': edges}


if __name__ == '__main__':
    graph = build()
    (ROOT / 'backend/src/pcquote/knowledge/games.json').write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + '\n')
    print(len(graph['nodes']), 'nodes', len(graph['edges']), 'edges')
