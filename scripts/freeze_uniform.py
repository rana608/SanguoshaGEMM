"""Freeze the uniform-deck release separately from historical timing records."""
import datetime,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT/'upstream'),*args])
expected='e8768851bd8054db9fd1b63cd6f1feca813590d7'
assert git('rev-parse','HEAD').decode().strip()==expected
rules=['src/server/gamerule.cpp','src/package/standard.cpp','src/package/standard-cards.cpp','src/package/standard-equips.h','src/package/thicket.cpp']
for name in rules:assert not git('diff','HEAD','--',name),name
editions={};decks=set()
for edition in ['baseline','optimized']:
    tests=read(ROOT/'evidence/uniform-deck'/edition/'engine/summary.json')
    records=read(ROOT/'evidence/uniform-deck'/edition/'records/summary.json')
    assert tests['passed']==13 and records['passed']==21
    name='SanguoshaGEMM-'+edition.title();binary=ROOT/'dist'/name/(name+'.exe')
    assert sha(binary)==tests['executableSha256']
    decks.add(tests['initialDrawPileSha256'])
    editions[edition]=dict(executableSha256=sha(binary),engineTests=13,recordTests=21)
assert len(decks)==1
isolation=read(ROOT/'evidence/uniform-deck/isolation/summary.json');assert isolation['passed']
names=set(git('diff','--name-only','HEAD','-z').decode().strip('\0').split('\0'))
names.update(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))
files=[ROOT/'upstream'/n for n in sorted(names) if n and (ROOT/'upstream'/n).is_file()]
for folder in ['launcher','scripts','docs','examples','licenses']:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
files.extend(ROOT/n for n in ['README.md','NEXT.md'])
manifest=dict(createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),upstream=expected,
              resourceVersion='uniform-large-v1',resourcePolicy='Same deck for every valid input and both editions',
              attackCapacity=800,rescueCapacity=800,drawPileCapacity=131072,initialDrawPileSha256=next(iter(decks)),
              algorithmVersions=['baseline-v1','transpose-v1.2'],editions=editions,isolation=isolation,
              unchangedRules=[dict(path=n,sha256=sha(ROOT/'upstream'/n)) for n in rules],
              sourceFiles=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in files],
              limitations=['Previous timings belong to previous binary/resource versions',
                           'No new performance benchmark or final GUI gameplay inspection in this change'])
data=json.dumps(manifest,ensure_ascii=False,indent=2)
for name in ['uniform-large-v1-manifest.json','current-manifest.json']:(ROOT/'evidence/frozen'/name).write_text(data,encoding='utf-8')
(ROOT/'evidence/frozen/uniform-large-v1.patch').write_bytes(git('diff','HEAD','--binary'))
print('Frozen uniform-large-v1: 26 deck/engine cases, 42 input/replay cases, same deck across both editions')
