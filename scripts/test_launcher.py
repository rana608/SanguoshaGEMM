"""Exercise native launch buttons offscreen, without desktop automation."""
import hashlib,json,pathlib,subprocess,tempfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
runtime=ROOT/'dist/SanguoshaGEMM-Launcher';exe=runtime/'SanguoshaGEMM-Launcher.exe'
out=ROOT/'evidence/launcher';out.mkdir(parents=True,exist_ok=True)

def run(*args):
    p=subprocess.run([str(exe),*map(str,args)],cwd=ROOT,capture_output=True,timeout=30)
    assert p.returncode==0,(args,p.returncode,p.stderr)
    return p

run('--self-test',out/'buttons.json')
buttons=json.loads((out/'buttons.json').read_text(encoding='utf-8'))
assert buttons['passed'] and buttons['buttonsResetAfterExit']
assert len({r['pid'] for r in buttons['editions']})==2
for entry in buttons['editions']:
    folder=ROOT/'dist'/('SanguoshaGEMM-'+entry['edition'])
    assert pathlib.Path(entry['program']).resolve()==folder/(folder.name+'.exe')
    assert pathlib.Path(entry['workingDirectory']).resolve()==folder
    assert entry['arguments']==['--gemm'] and entry['running'] and not entry['enabled']

with tempfile.TemporaryDirectory(prefix='missing-clients-',dir=out) as tmp:
    folder=pathlib.Path(tmp).resolve();assert folder.is_relative_to(out.resolve())
    run('--check',folder,out/'missing.json')
    missing=json.loads((out/'missing.json').read_text(encoding='utf-8'))
    assert all(not r['enabled'] and r['status'] for r in missing['editions'])
    # Check the unpacked bundle's child-folder layout independently of workspace siblings.
    child=folder/'SanguoshaGEMM-Baseline';child.mkdir()
    (child/'SanguoshaGEMM-Baseline.exe').touch()
    run('--check',folder,out/'one-present.json')
    one=json.loads((out/'one-present.json').read_text(encoding='utf-8'))['editions']
    assert one[0]['enabled'] and not one[1]['enabled']
    assert pathlib.Path(one[0]['program']).resolve()==child/'SanguoshaGEMM-Baseline.exe'

run('--render',out/'launcher.png')
assert (out/'launcher.png').stat().st_size>10000
manifest=ROOT/'evidence/frozen/current-manifest.json'
if not manifest.exists():manifest=ROOT/'evidence/frozen/expanded-v1-manifest.json'
frozen=json.loads(manifest.read_text(encoding='utf-8'))
for edition in ['baseline','optimized']:
    name='SanguoshaGEMM-'+edition.title();program=ROOT/'dist'/name/(name+'.exe')
    assert hashlib.sha256(program.read_bytes()).hexdigest()==frozen['editions'][edition]['executableSha256']
summary=dict(passed=True,realButtonLaunches=2,distinctClients=True,clientsOpenedWithGemm=True,
             correctWorkingDirectories=True,buttonsResetAfterExit=True,missingClientsDisabled=True,
             childAndSiblingLayouts=True,offscreenRender=True,gameBinariesUnchanged=True,
             launcherSha256=hashlib.sha256(exe.read_bytes()).hexdigest())
(out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
