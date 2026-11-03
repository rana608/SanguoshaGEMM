"""Black-box tests: actual QSanguosha executable, independent integer oracle."""
import argparse,json,os,pathlib,random,subprocess,time
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');parser.add_argument('--edition',choices=['baseline','optimized'],default='baseline');parser.add_argument('--output-dir',type=pathlib.Path);args=parser.parse_args()
selected={'baseline':'baseline-v1','optimized':'transpose-v1.2'}[args.edition]
runtime=root/('dist/SanguoshaGEMM-'+args.edition.title());exe=runtime/('SanguoshaGEMM-'+args.edition.title()+'.exe')
out=(args.output_dir or root/'evidence/versions'/args.edition/'engine').resolve();out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,QT_QPA_PLATFORM='offscreen')
cases=[]
def add(name,a,b,algorithm=None,**extra):
    algorithm=algorithm or selected
    cases.append((name,dict(A=a,B=b,algorithm=algorithm,speed=2,**extra)))
add('example',[[1,2],[3,0]],[[2,1],[1,2]])
if not args.smoke:
    for a in range(10):
        for b in range(10):add(f'scalar-{a}-{b}',[[a]],[[b]])
    for alg in [selected]:
        add('maximum-'+alg,[[9,9],[9,9]],[[9,9],[9,9]],alg)
        add('identity-'+alg,[[9,8],[7,6]],[[1,0],[0,1]],alg)
        add('zeros-'+alg,[[0,0],[0,0]],[[0,0],[0,0]],alg)
        rng=random.Random(20261103)
        for n in range(16):
            m,k,p=[rng.randint(1,2) for _ in range(3)]
            a=[[rng.randrange(10) for _ in range(k)] for _ in range(m)]
            b=[[rng.randrange(10) for _ in range(p)] for _ in range(k)]
            add(f'random-{alg}-{n}',a,b,alg)
    add('controls',[[1,2],[3,0]],[[2,1],[1,2]],testControls=True)
    for speed in [0,1,2]:
        add('speed-'+str(speed),[[2]],[[3]])
        cases[-1][1]['speed']=speed
    for fault in ['no-rescue','empty-deck','no-range']:
        add('fault-'+fault,[[1,1],[1,1]],[[1,1],[1,1]],fault=fault)
summary=[]
for name,case in cases:
    inp=out/(name+'.input.json');result=out/(name+'.json')
    inp.write_text(json.dumps(case),encoding='utf-8')
    result.unlink(missing_ok=True)
    t=time.perf_counter()
    p=subprocess.run([str(exe),'--gemm-case',str(inp),str(result)],cwd=runtime,env=env,capture_output=True,timeout=45)
    (out/(name+'.log')).write_bytes(p.stdout+p.stderr)
    if not result.exists():raise AssertionError((name,p.returncode,(p.stdout+p.stderr)[-2000:]))
    r=json.loads(result.read_text(encoding='utf-8'))
    if 'fault' in case:
        assert p.returncode==1 and r['status']=='failed',(name,r)
    else:
        expected=[[sum(x*y for x,y in zip(row,col)) for col in zip(*case['B'])] for row in case['A']]
        assert p.returncode==0 and r['status']=='complete' and r['C']==expected,(name,p.returncode,r)
        assert r['edition']==args.edition and r['algorithm']==selected
        assert len(r['trace'])==r['completed']==r['tasks'],name
        assert all(x['caopiHp']==1 for x in r['trace']),name
        assert r['rescues']==r['tasks'] and r['damagePoints']==r['tasks'] and r['fangzhu']==r['tasks'],(name,r)
        assert r['drawnCards']==sum(map(sum,expected)),name
        if name=='controls':assert r['controlTestPassed']
        if name.startswith('identity-'):assert r['completed']=={'baseline-v1':60,'sparse-v1.1':30,'transpose-v1.2':4}[case['algorithm']]
        if args.edition=='baseline':
            assert r['tasks']==len(case['B'][0])*sum(map(sum,case['A']))
            previous=root/'evidence/engine'/(name+'.json')
            if previous.exists():
                old=json.loads(previous.read_text(encoding='utf-8'))
                # Resource versions have different card IDs and rescue reserves.
                for key in ['C','tasks']:
                    assert r[key]==old[key],(name,'frozen baseline changed',key)
                semantic=['step','i','j','k','before','after','caopiHp','originalI','originalJ']
                assert [{k:t[k] for k in semantic} for t in r['trace']]==[{k:t[k] for k in semantic} for t in old['trace']]
    summary.append(dict(name=name,status=r['status'],tasks=r['tasks'],completed=r['completed'],engineMs=r['engineMs'],processSeconds=time.perf_counter()-t))
    print(name,r['status'],r.get('C'),round(r['engineMs'],3),'ms',flush=True)
(out/('smoke-summary.json' if args.smoke else 'summary.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('PASS',len(summary))
