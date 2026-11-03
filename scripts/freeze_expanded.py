"""Freeze expanded binaries and their own evidence; never relabel old timings as new."""
import datetime, hashlib, json, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT/'upstream'),*args])

upstream='e8768851bd8054db9fd1b63cd6f1feca813590d7'
assert git('rev-parse','HEAD').decode().strip()==upstream
rules=['src/server/gamerule.cpp','src/package/standard.cpp','src/package/standard-cards.cpp',
       'src/package/standard-equips.h','src/package/thicket.cpp']
for name in rules:assert not git('diff','HEAD','--',name),name
suite=read(ROOT/'evidence/expanded/suite-v1/summary.json')
audit=read(ROOT/'evidence/expanded/suite-v1/integrity.json')
assert suite['status']=='complete' and suite['passed']==12 and suite['failed']==0
assert audit['passed'] and audit['nativeRecords']==96 and audit['summarySha256']==sha(ROOT/'evidence/expanded/suite-v1/summary.json')
editions={}
for edition in ['baseline','optimized']:
    label=edition.title();binary=ROOT/'dist'/('SanguoshaGEMM-'+label)/('SanguoshaGEMM-'+label+'.exe')
    assert sha(binary)==suite['run']['executableSha256'][edition]
    tests=read(ROOT/'evidence/expanded/regression'/edition/'engine/summary.json')
    records=read(ROOT/'evidence/expanded/regression'/edition/'records/summary.json')
    assert len(tests)==127 and records['passed']==21
    editions[edition]=dict(executableSha256=sha(binary),engineTests=len(tests),recordTests=records['passed'])
isolation=read(ROOT/'evidence/expanded/regression/isolation/summary.json');assert isolation['passed']
edges=read(ROOT/'evidence/expanded/edges/summary.json');assert edges['passed']==16
for case in edges['cases']:
    assert case['executableSha256']==editions[case['edition']]['executableSha256']
names=set(git('diff','--name-only','HEAD','-z').decode().strip('\0').split('\0'))
names.update(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))
files=[ROOT/'upstream'/name for name in sorted(names) if name and (ROOT/'upstream'/name).is_file()]
for folder in ['scripts','docs','examples','licenses']:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.extend(ROOT/name for name in ['README.md','NEXT.md'])
manifest=dict(createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),upstream=upstream,
              resourceVersion='expanded-v1',maxElement=100,maxDimension=2,
              attackCapacity=800,rescueCapacity=800,drawPileCapacity=131072,
              algorithmVersions=['baseline-v1','transpose-v1.2'],editions=editions,isolation=isolation,expandedEdgeTests=edges,
              benchmark=suite['run'],integrity=audit,
              unchangedRules=[dict(path=n,sha256=sha(ROOT/'upstream'/n)) for n in rules],
              sourceFiles=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files],
              limitations=['No final GUI verification of expanded hands or animations',
                           '3x3 and 4x4 cancelled by user; dimensions remain 1..2',
                           'Old 96-case suite timings apply only to preserved small-v1 binaries'])
(ROOT/'evidence/frozen/expanded-v1-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'evidence/frozen/expanded-v1.patch').write_bytes(git('diff','HEAD','--binary'))
print('Frozen expanded-v1: 96 measured/warmup calls, 296 regression cases, 16 expanded edge/replay tests, isolation, original rules unchanged')
