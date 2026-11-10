import json,re,pathlib
root=pathlib.Path(__file__).resolve().parents[2]
def read(name):return json.loads(re.search(r'```json\s*(.*?)```',(root/'docs/research'/name).read_text(),re.S)[1])
r=read('2026-11-11-game-requirements-sources.md');b=read('2026-11-11-game-benchmark-sources.md')
nodes={};edges=[]
def node(id,node_type,**data):
 if 'kind' in data:data['source_kind']=data.pop('kind')
 nodes[id]={**data,'id':id,'kind':node_type};return id
def edge(a,rel,z):
 e={'from':a,'relation':rel,'to':z}
 if rel.startswith('REQUIRES_'):e.update(operator='any',alternative_group=a+':'+rel)
 edges.append(e)
def hw(d,category):
 variant=':vram'+str(d['vram_gb']) if d.get('vram_gb') else ''
 return node('hardware:'+d['id']+variant,'hardware',category=category,**{k:v for k,v in d.items() if k!='id'})
for g in r['games']:
 gid=node('game:'+g['game_id'],'game',name=g['name'],aliases=g['aliases'])
 sid=node('source:'+g['game_id'],'source',**g['source'],reviewed=True,review_after='2027-02-11')
 for p in g['profiles']:
  rid=node(gid+':'+p['id'],'requirement',tier=p['id'],**{k:v for k,v in p.items() if k not in ('id','cpu_alternatives','gpu_alternatives')})
  edge(gid,'HAS_REQUIREMENT',rid);edge(rid,'SUPPORTED_BY',sid)
  for cat in ('cpu','gpu'):
   for d in p[cat+'_alternatives']:edge(rid,'REQUIRES_'+cat.upper(),hw(d,cat))
sid=node('source:'+b['source']['id'],'source',url=b['source']['methodology_url'],publisher=b['source']['owner'],accessed_at=b['accessed_at'],reviewed=True,review_after='2027-02-11',published_at=b['source']['published_at'])
for o in b['observations']:
 c=b['contexts'][o['context']];gid='game:'+('overwatch' if c['game']=='overwatch-2' else c['game'].replace('-','_'))
 mid=node('measurement:'+o['id'],'measurement',**{k:v for k,v in o.items() if k not in ('id','context','gpu')},context=c,platform=b['platform'])
 gpu=hw({'id':re.sub('[^a-z0-9]+','-',o['gpu'].lower()),'label':o['gpu'],'model':re.sub(r'\W','',o['gpu'].replace('GeForce RTX ','')).lower(),'vram_gb':o['vram_gb']},'gpu')
 cpu=hw({'id':'amd-ryzen-7-9800x3d','label':b['platform']['cpu']},'cpu')
 edge(gid,'HAS_MEASUREMENT',mid);edge(mid,'SUPPORTED_BY',sid);edge(mid,'TESTED_GPU',gpu);edge(mid,'TESTED_CPU',cpu)
graph={'version':'2026-11-11.1','nodes':list(nodes.values()),'edges':edges}
(root/'backend/src/pcquote/knowledge/games.json').write_text(json.dumps(graph,ensure_ascii=False,indent=2)+'\n')
print(len(nodes),'nodes',len(edges),'edges')
