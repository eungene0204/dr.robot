"""Blender Open Data benchmarks (CC0), ported from buildmate (pipeline/adapters/blender.mjs, tools/blender.py).

The official snapshot ZIP is downloaded at most every 7 days and streamed: the
1 GB+ JSONL inside is never extracted. Only complete three-scene submissions from a
single device count, and scores are never mixed across Blender versions.
"""

from __future__ import annotations

import collections
import functools
import hashlib
import json
import math
import os
import re
import statistics
import time
import zipfile
from pathlib import Path

from pcquote.collector.client import SourceClient, utc_iso
from pcquote.collector.parse import SourceError

BLENDER_URL = "https://opendata.blender.org/snapshots/opendata-latest.zip"
MAX_ARCHIVE = 250_000_000
CACHE_DAYS = 7


def download(client: SourceClient, path: Path, force: bool = False) -> dict | None:
    """Fetch the archive unless a copy younger than 7 days exists. Returns the new meta, or None when cached."""
    if not force and path.exists() and time.time() - path.stat().st_mtime < CACHE_DAYS * 86400:
        return None
    # This URL is the official downloadable CC0 data export, not an HTML crawl. HTTP errors,
    # rate limits and the size limit apply; robots.txt directory-index exclusions concern crawling.
    r = client.raw(BLENDER_URL, stream=True)
    digest, size = hashlib.sha256(), 0
    tmp = path.with_suffix(path.suffix + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "wb") as f:
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > MAX_ARCHIVE:
                    raise SourceError("벤치마크 ZIP 용량 제한")
                digest.update(chunk)
                f.write(chunk)
    finally:
        r.close()
    os.replace(tmp, path)
    return {"sourceUrl": BLENDER_URL, "hash": digest.hexdigest(), "observedAt": utc_iso(), "lastModified": r.headers.get("last-modified"),
            "bytes": size}


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(name):
    name=re.sub(r'\([^)]*\)', '', name).lower()
    name=re.sub(r'^\d+(?:st|nd|rd|th)\s+gen\s+', '', name)
    name=re.sub(r'\b\d+-core processor\b|\bprocessor\b','',name)
    return re.sub(r'[^a-z0-9]','',name)

def aggregate(archive, devices):
    names=collections.defaultdict(list)
    for d in devices:
        if d.get('benchmarkName'):names[normalize(d['benchmarkName'])].append(d['id'])
    needles=list({d['benchmarkName'].split(' ')[-1].encode() for d in devices if d.get('benchmarkName')})
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
                device=ds[0];parts=names.get(normalize(device.get('name','')))
                part=tuple(parts) if parts else None
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
        for part_id in part:
            output.append({'partId':part_id,'version':version,'backend':backend,'sceneChecksums':checksums,'score':statistics.median(scores),'samples':len(scores),'min':min(scores),'max':max(scores),'lastSubmissionAt':max(dates[key]),'metric':'blender_samples_per_minute_sum','unit':'samples/min','scope':'chip-model','scenes':['monster','junkshop','classroom']})
    return {'scannedSubmissions':scanned,'groups':output,'snapshotFile':filename,'license':'CC0-1.0'}



def _natural(a: str, b: str) -> int:
    """String.localeCompare(b, undefined, {numeric: true}) for version strings."""
    ka = [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|\D+", a)]
    kb = [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|\D+", b)]
    return (ka > kb) - (ka < kb)


def select_benchmarks(groups: list[dict], minimum_samples: int = 3) -> list[dict]:
    valid = [r for r in groups if r["samples"] >= minimum_samples and isinstance(r["score"], (int, float)) and math.isfinite(r["score"])
             and r["score"] > 0 and r["backend"] in ("CPU", "OPTIX")]
    versions = list(dict.fromkeys(r["version"] for r in valid))
    coverage = {v: len({r["partId"] for r in valid if r["version"] == v}) for v in versions}
    versions.sort(key=functools.cmp_to_key(lambda a, b: (coverage[b] - coverage[a]) or _natural(b, a)))
    if not versions:
        return []
    version = versions[0]
    rows = [r for r in valid if r["version"] == version]
    result = []
    for part_id in dict.fromkeys(r["partId"] for r in rows):
        options = sorted((r for r in rows if r["partId"] == part_id), key=lambda r: -r["samples"])
        result.append(options[0])
    return result
