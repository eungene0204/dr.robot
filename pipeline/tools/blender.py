#!/usr/bin/env python3
"""Stream the official CC0 JSONL snapshot; never extract the 1GB+ file to disk."""
import argparse,collections,json,math,re,statistics,zipfile

def normalize(name):
    name=re.sub(r'\([^)]*\)', '', name).lower()
    name=re.sub(r'\b\d+-core processor\b|\bprocessor\b','',name)
    return re.sub(r'[^a-z0-9]','',name)

def aggregate(archive, devices):
    names={normalize(d['benchmarkName']):d['id'] for d in devices if d.get('benchmarkName')}
    needles=[d['benchmarkName'].split(' ')[-1].encode() for d in devices if d.get('benchmarkName')]
    groups=collections.defaultdict(list);dates=collections.defaultdict(list);scanned=0
    with zipfile.ZipFile(archive) as z:
        filename=next(n for n in z.namelist() if n.endswith('.jsonl'))
        for line in z.open(filename):
            scanned+=1
            if needles and not any(n in line for n in needles):continue
            try:record=json.loads(line)
            except (ValueError,TypeError):continue
            if not isinstance(record,dict) or not isinstance(record.get('data'),list):continue
            scenes={};identity=None;bad=False
            for row in record.get('data',[]):
                if not isinstance(row,dict):bad=True;break
                ds=row.get('device_info',{}).get('compute_devices',[])
                if len(ds)!=1:bad=True;break
                device=ds[0];part=names.get(normalize(device.get('name','')))
                if not part:bad=True;break
                version=row.get('blender_version',{}).get('version')
                backend=row.get('device_info',{}).get('device_type')
                scene=row.get('scene',{});label=scene.get('label')
                if label not in ('monster','junkshop','classroom'):continue
                score=row.get('stats',{}).get('samples_per_minute')
                if not isinstance(score,(int,float)) or not math.isfinite(score) or score<=0:bad=True;break
                current=(part,version,backend)
                if identity is not None and identity!=current:bad=True;break
                identity=current
                if label in scenes:bad=True;break
                scenes[label]=(score,scene.get('checksum'))
            if bad or identity is None or set(scenes)!=set(('monster','junkshop','classroom')):continue
            # Same version/backend/scenes only. One score per complete submission.
            checksums=tuple(scenes[k][1] for k in sorted(scenes))
            key=identity+checksums
            groups[key].append(sum(v[0] for v in scenes.values()))
            dates[key].append(record.get('created_at',''))
    output=[]
    for key,scores in groups.items():
        part,version,backend,*checksums=key
        output.append({'partId':part,'version':version,'backend':backend,'sceneChecksums':checksums,'score':statistics.median(scores),'samples':len(scores),'min':min(scores),'max':max(scores),'lastSubmissionAt':max(dates[key]),'metric':'blender_samples_per_minute_sum','unit':'samples/min','scope':'chip-model','scenes':['monster','junkshop','classroom']})
    return {'scannedSubmissions':scanned,'groups':output,'snapshotFile':filename,'license':'CC0-1.0'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('registry');p.add_argument('output');args=p.parse_args()
    registry=json.load(open(args.registry))
    result=aggregate(args.archive,registry['products'])
    with open(args.output,'w') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'scannedSubmissions':result['scannedSubmissions'],'benchmarkGroups':len(result['groups'])}))
