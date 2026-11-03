"""Export complete runtime/source ZIPs while excluding local tools and preferences."""
import hashlib,json,pathlib,subprocess,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
dest=root/'dist'
excluded={'config.ini','sanguosha.ini'}

def create(name, files):
    path=dest/name
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as archive:
        for source,relative in files:archive.write(source,relative)
    with zipfile.ZipFile(path) as archive:
        bad=archive.testzip()
        assert bad is None,bad
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    print(name,path.stat().st_size,digest,flush=True)
    return dict(file=name,bytes=path.stat().st_size,sha256=digest)

runtime_packages=[]
for edition in ['Baseline','Optimized']:
    folder='SanguoshaGEMM-'+edition;runtime=dest/folder
    files=[(p,folder+'/'+p.relative_to(runtime).as_posix()) for p in sorted(runtime.rglob('*'))
           if p.is_file() and p.name.lower() not in excluded
           and not (p.name.lower().startswith('config-') and p.suffix=='.ini')
           and 'records' not in p.relative_to(runtime).parts]
    assert any(p.suffix=='.exe' for p,_ in files),folder
    runtime_packages.append((folder+'-windows.zip',files))
sources=[]
if (root/'upstream/.git').exists():
    names=subprocess.check_output(['git','-C',str(root/'upstream'),'ls-files','-z','--cached','--others','--exclude-standard']).decode().split('\0')
    sources += [(root/'upstream'/n,'SanguoshaGEMM-source/upstream/'+n) for n in sorted(set(names)) if n and (root/'upstream'/n).is_file()]
else:
    sources += [(p,'SanguoshaGEMM-source/upstream/'+p.relative_to(root/'upstream').as_posix())
                for p in (root/'upstream').rglob('*') if p.is_file() and 'tools' not in p.relative_to(root/'upstream').parts]
for folder in ['launcher','scripts','docs','examples','licenses','evidence']:
    sources += [(p,'SanguoshaGEMM-source/'+p.relative_to(root).as_posix()) for p in sorted((root/folder).rglob('*'))
                if p.is_file() and '__pycache__' not in p.parts]
for name in ['README.md','NEXT.md']:sources.append((root/name,'SanguoshaGEMM-source/'+name))
manifest=[create(name,files) for name,files in runtime_packages]
manifest.append(create('SanguoshaGEMM-source.zip',sources))
test_files=[]
for folder in ['examples','evidence/versions/suite-v1','evidence/expanded/suite-v1','evidence/uniform-deck']:
    test_files.extend((p,'SanguoshaGEMM-tests/'+p.relative_to(root).as_posix()) for p in sorted((root/folder).rglob('*')) if p.is_file())
for script in ['compare.py','benchmark.py','benchmark_suite.py','build_test_suite.py','verify_suite.py','build_expanded_suite.py','verify_expanded.py']:
    test_files.append((root/'scripts'/script,'SanguoshaGEMM-tests/scripts/'+script))
test_files.append((root/'docs/TEST_SUITE.md','SanguoshaGEMM-tests/README.md'))
for doc in ['TEST_SUITE.md','TEST_SUITE_RESULTS.md','SCALING.md','EXPANDED_RESULTS.md','UNIFORM_DECK.md']:
    test_files.append((root/'docs'/doc,'SanguoshaGEMM-tests/docs/'+doc))
manifest.append(create('SanguoshaGEMM-test-suite.zip',test_files))
(dest/'SHA256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
