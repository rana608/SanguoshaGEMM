"""Expanded resource failures, input limits and deterministic replay through both native engines."""
import hashlib, json, pathlib, subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
out=ROOT/'evidence/expanded/edges';out.mkdir(parents=True,exist_ok=True)
summary=[]
stable=['A','B','algorithm','transposed','tasks','completed','status','C','resourceVersion',
        'initialPlayers','initialDrawPile','initialWeaponId','finalPlayers','trace',
        'activeCardUses','rescues','damagePoints','fangzhu','drawnCards','drawPileCapacity']
for edition in ['baseline','optimized']:
    runtime=ROOT/'dist'/('SanguoshaGEMM-'+edition.title());exe=runtime/(runtime.name+'.exe')
    def run(name,payload,code):
        inp=out/(edition+'-'+name+'.input.json');result=out/(edition+'-'+name+'.json')
        inp.write_text(json.dumps(payload),encoding='utf-8');result.unlink(missing_ok=True)
        p=subprocess.run([str(exe),'--gemm-case',str(inp),str(result)],cwd=runtime,capture_output=True,timeout=600)
        assert p.returncode==code,(edition,name,p.returncode,p.stderr)
        r=json.loads(result.read_text(encoding='utf-8'))
        if code:
            assert r['error'] and r['status']!='complete'
        else:
            oracle=[[sum(x*y for x,y in zip(row,col)) for col in zip(*r['B'])] for row in r['A']]
            assert r['status']=='complete' and r['C']==oracle
        summary.append(dict(edition=edition,name=name,status=r['status'],executableSha256=hashlib.sha256(exe.read_bytes()).hexdigest()))
        print(edition,name,r['status'],flush=True)
        return r
    for fault in ['no-rescue','empty-deck','no-range']:
        r=run(fault,dict(A=[[10,10],[10,10]],B=[[10,10],[10,10]],speed=2,fault=fault),1)
        assert r['resourceVersion']=='expanded-v1' and r['completed']==0
    for value in [101,100.1,1e100]:
        r=run('invalid-'+str(value),dict(A=[[value]],B=[[1]],speed=2),2)
        assert 'C' not in r
    r=run('controls',dict(A=[[10,1],[0,10]],B=[[1,2],[3,4]],speed=2,testControls=True),0)
    assert r['controlTestPassed'] and r['drawPileCapacity']==131072
    replay=run('replay',r,0)
    assert all(r[k]==replay[k] for k in stable)
(out/'summary.json').write_text(json.dumps(dict(passed=len(summary),cases=summary),indent=2),encoding='utf-8')
print('PASS',len(summary))
