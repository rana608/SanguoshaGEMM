"""Freeze source/binary identifiers and real-engine evidence without committing Git."""
import datetime, hashlib, json, os, pathlib, platform, subprocess

root=pathlib.Path(__file__).resolve().parents[1]
upstream=root/'upstream'
if not (upstream/'.git').exists():
    raise SystemExit('Freeze requires the original Git checkout; exported source already includes evidence/frozen/.')
expected='e8768851bd8054db9fd1b63cd6f1feca813590d7'
def git(*args):return subprocess.check_output(['git','-C',str(upstream),*args])
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
assert git('rev-parse','HEAD').decode().strip()==expected
rules=['src/server/gamerule.cpp','src/package/standard.cpp','src/package/standard-cards.cpp',
       'src/package/standard-equips.h','src/package/thicket.cpp']
unchanged=[]
for name in rules:
    # Git normalizes line endings before comparison; preserve raw working hashes too.
    assert not git('diff','HEAD','--',name), name
    unchanged.append(dict(path=name,sha256=sha(upstream/name)))
paths=set(git('diff','--name-only','HEAD','-z').decode().strip('\0').split('\0'))
paths.update(git('ls-files','--others','--exclude-standard','-z').decode().strip('\0').split('\0'))
changed=[dict(path='upstream/'+p,sha256=sha(upstream/p)) for p in sorted(paths) if p and (upstream/p).is_file()]
for folder in ['scripts','docs','examples','licenses']:
    changed += [dict(path=p.relative_to(root).as_posix(),sha256=sha(p)) for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
for name in ['README.md','NEXT.md']:
    changed.append(dict(path=name,sha256=sha(root/name)))
editions={}
for edition in ['baseline','optimized']:
    folder=root/'evidence/versions'/edition
    tests=json.loads((folder/'engine/summary.json').read_text(encoding='utf-8'))
    records=json.loads((folder/'records/summary.json').read_text(encoding='utf-8'))
    assert len(tests)==127 and records['passed']==21, 'Run both verification suites before freezing'
    editions[edition]=dict(executableSha256=sha(root/('dist/SanguoshaGEMM-'+edition.title())/('SanguoshaGEMM-'+edition.title()+'.exe')),
                          engineTests=len(tests),recordTests=records['passed'])
isolation=json.loads((root/'evidence/versions/isolation/summary.json').read_text(encoding='utf-8'))
assert isolation['passed']
benchmark=json.loads((root/'evidence/versions/benchmark/summary.json').read_text(encoding='utf-8'))
suite=json.loads((root/'evidence/versions/suite-v1/summary.json').read_text(encoding='utf-8'))
assert suite['status']=='complete' and suite['passed']==suite['uniqueInputs'] and suite['failed']==0
assert suite['run']['executableSha256']=={edition:data['executableSha256'] for edition,data in editions.items()}
integrity=json.loads((root/'evidence/versions/suite-v1/integrity.json').read_text(encoding='utf-8'))
assert integrity['passed'] and integrity['summarySha256']==sha(root/'evidence/versions/suite-v1/summary.json')
manifest=dict(upstream=expected,createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              algorithmVersions=['baseline-v1','transpose-v1.2'],
              environment=dict(os=platform.platform(),processor=os.environ.get('PROCESSOR_IDENTIFIER'),
                               qt='5.5.1',compiler='MinGW 4.9.2',target='win32-release',backend='Qt offscreen'),
              editions=editions,unchangedRules=unchanged,
              sourceFiles=changed,isolation=isolation,singleCaseDemo=benchmark,
              benchmarkSuite=dict(uniqueInputs=suite['uniqueInputs'],passed=suite['passed'],run=suite['run'],groups=suite['groups'],integrity=integrity,
                                  summarySha256=sha(root/'evidence/versions/suite-v1/summary.json')),
              limitations=['Final GUI layout and interactions not re-tested after user stopped desktop automation',
                           'Full ordinary-match regression and clean-machine validation not performed'])
folder=root/'evidence/frozen';folder.mkdir(exist_ok=True)
(folder/'two-editions-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'two-editions.patch').write_bytes(git('diff','HEAD','--binary'))
print('Frozen',len(changed),'files; both editions, isolated runtime; unchanged original rule files:',len(unchanged))
