"""Run both actual executables together, from one cwd, without desktop automation."""
import argparse, json, pathlib, subprocess, time
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=pathlib.Path);args=parser.parse_args()
out=(args.output_dir or root/'evidence/versions/isolation').resolve();out.mkdir(parents=True,exist_ok=True)
sentinel=out/'config.ini'
sentinel.write_text('[Isolation]\nvalue=must-not-be-touched\n',encoding='utf-8')
original=sentinel.read_bytes()
case=out/'same-input.json'
case.write_text(json.dumps(dict(A=[[3]],B=[[3]],speed=0,testListener=True)),encoding='utf-8')
processes={}
for edition in ['baseline','optimized']:
    runtime=root/('dist/SanguoshaGEMM-'+edition.title())
    exe=runtime/('SanguoshaGEMM-'+edition.title()+'.exe')
    result=out/(edition+'.json');result.unlink(missing_ok=True)
    processes[edition]=subprocess.Popen([str(exe),'--gemm-case',str(case),str(result)],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
time.sleep(0.3)
assert all(p.poll() is None for p in processes.values()),'Processes did not overlap'
reports={}
for edition,p in processes.items():
    stdout,stderr=p.communicate(timeout=60)
    assert p.returncode==0,(edition,p.returncode,stderr)
    r=json.loads((out/(edition+'.json')).read_text(encoding='utf-8'))
    assert r['edition']==edition and r['C']==[[9]]
    settings=pathlib.Path(r['settingsPath'])
    assert settings.resolve()==(root/('dist/SanguoshaGEMM-'+edition.title())/('config-'+edition+'.ini')).resolve()
    assert settings.exists()
    reports[edition]=r
assert reports['baseline']['serverPort']!=reports['optimized']['serverPort']
assert sentinel.read_bytes()==original,'Shared launch-directory config was modified'
for edition in processes:
    runtime=root/('dist/SanguoshaGEMM-'+edition.title())
    wrong='transpose-v1.2' if edition=='baseline' else 'baseline-v1'
    inp=out/(edition+'-mismatch.input.json');result=out/(edition+'-mismatch.json')
    inp.write_text(json.dumps(dict(A=[[1]],B=[[1]],algorithm=wrong)),encoding='utf-8')
    result.unlink(missing_ok=True)
    p=subprocess.run([str(runtime/('SanguoshaGEMM-'+edition.title()+'.exe')),'--gemm-case',str(inp),str(result)],cwd=out,capture_output=True,timeout=10)
    assert p.returncode==2
    assert json.loads(result.read_text(encoding='utf-8'))['status']=='invalid-input'

summary=dict(passed=True,simultaneousProcesses=2,algorithmMismatchRejections=2,sharedCwdUntouched=True,
             settings={e:r['settingsPath'] for e,r in reports.items()},ports={e:r['serverPort'] for e,r in reports.items()})
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('PASS: concurrent execution, separate configs/ports/results, fixed algorithms')
