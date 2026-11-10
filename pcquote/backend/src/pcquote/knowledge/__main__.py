import json
import sys
from . import graph

g=graph()
if len(sys.argv)>1 and sys.argv[1]=='resolve':
    print(json.dumps(g.resolve(' '.join(sys.argv[2:])),ensure_ascii=False,indent=2))
else:
    g.validate()
    print(json.dumps({'version':g.data['version'],'games':len(g.games()),'nodes':len(g.nodes),'edges':len(g.data['edges']),'valid':True}))
