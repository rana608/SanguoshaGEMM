"""Verify one fixed deck across small/large/zero inputs and both real engine editions."""
import argparse,hashlib,json,pathlib,re,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--edition',required=True,choices=['baseline','optimized']);args=p.parse_args()
edition=args.edition;runtime=ROOT/'dist'/('SanguoshaGEMM-'+edition.title());exe=runtime/(runtime.name+'.exe')
out=ROOT/'evidence/uniform-deck'/edition/'engine';out.mkdir(parents=True,exist_ok=True)
cases=[('zero',[[0,0],[0,0]],[[0,0],[0,0]],{}),
       ('one',[[1]],[[1]],{}),('scalar-9',[[9]],[[9]],{}),('scalar-10',[[10]],[[10]],{}),
       ('example',[[1,2],[3,0]],[[2,1],[1,2]],{}),
       ('all-9',[[9,9],[9,9]],[[9,9],[9,9]],{}),
       ('all-100',[[100,100],[100,100]],[[100,100],[100,100]],{}),
       ('rectangle',[[8,7],[9,9]],[[7],[8]],{}),
       ('zero-right',[[7,3],[4,9]],[[0,0],[0,0]],{}),
       ('controls',[[1,2],[3,0]],[[2,1],[1,2]],dict(testControls=True))]
for fault in ['no-rescue','empty-deck','no-range']:
    cases.append((fault,[[1,1],[1,1]],[[1,1],[1,1]],dict(fault=fault)))
summary=[];pile_hash=None
for name,a,b,extra in cases:
    inp=out/(name+'.input.json');result=out/(name+'.json')
    inp.write_text(json.dumps(dict(A=a,B=b,speed=2,**extra)),encoding='utf-8');result.unlink(missing_ok=True)
    run=subprocess.run([str(exe),'--gemm-case',str(inp),str(result)],cwd=runtime,capture_output=True,timeout=180)
    assert result.exists(),(name,run.returncode,run.stderr)
    r=json.loads(result.read_text(encoding='utf-8'))
    assert r['edition']==edition and r['resourceVersion']=='uniform-large-v1'
    assert r['attackCapacity']==r['rescueCapacity']==800
    assert len(r['initialPlayers'][1]['hand'])==(0 if name=='no-rescue' else 800)
    if name=='empty-deck':assert r['drawPileCapacity']==0 and r['initialDrawPile']==[]
    else:
        assert r['drawPileCapacity']==len(r['initialDrawPile'])==len(set(r['initialDrawPile']))==131072
        digest=hashlib.sha256(json.dumps(r['initialDrawPile'],separators=(',',':')).encode()).hexdigest()
        if pile_hash is None:pile_hash=digest
        assert pile_hash==digest,'Deck differs between inputs'
    if 'fault' in extra:
        assert run.returncode==1 and r['status']=='failed' and r['completed']==0 and r['error']
    else:
        expected=[[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
        assert run.returncode==0 and r['status']=='complete' and r['C']==expected
        m,k,n=len(a),len(b),len(b[0])
        direct=sum(a[i][q] for i in range(m) for j in range(n) for q in range(k) if b[q][j])
        reverse=sum(b[q][j] for i in range(m) for j in range(n) for q in range(k) if a[i][q])
        count=n*sum(map(sum,a)) if edition=='baseline' else min(direct,reverse)
        assert r['tasks']==r['completed']==r['activeCardUses']==r['rescues']==r['fangzhu']==r['damagePoints']==len(r['trace'])==count
        assert r['transposed']==(edition=='optimized' and reverse<direct)
        assert r['drawnCards']==sum(map(sum,expected))
        initial={x['id']:x for x in r['initialPlayers']};final={x['id']:x for x in r['finalPlayers']}
        for x in r['initialPlayers']:
            if x['general']=='caopi':assert final[x['id']]['hp']==1
            pos=re.fullmatch(r'C\[(\d+),(\d+)\]',x['label'])
            if pos:
                i,j=[int(v)-1 for v in pos.groups()]
                assert not x['hand'] and final[x['id']]['handCount']==expected[i][j]
        stock=set(r['initialDrawPile']);used=set();shots=set();rescues=set();hands={}
        for t in r['trace']:
            ids=set(t['drawnCardIds']);red=set(t['rescueCardIds'])
            assert t['caopiHp']==1 and t['before']==hands.get(t['output'],0)
            assert len(ids)==len(t['drawnCardIds'])==t['after']-t['before']==initial[t['target']]['maxhp']-1
            assert ids<=stock and ids.isdisjoint(used)
            assert len(red)==1 and red<=set(r['initialPlayers'][1]['hand']) and red.isdisjoint(rescues)
            assert t['slashId'] in r['initialPlayers'][0]['hand'] and t['slashId'] not in shots
            used.update(ids);rescues.update(red);shots.add(t['slashId']);hands[t['output']]=t['after']
        if name=='controls':assert r['controlTestPassed']
    summary.append(dict(name=name,status=r['status'],C=r['C'],tasks=r['tasks'],completed=r['completed'],drawnCards=r['drawnCards']))
    print(edition,name,r['status'],r['C'],flush=True)
report=dict(passed=len(summary),edition=edition,resourceVersion='uniform-large-v1',attackCapacity=800,rescueCapacity=800,
            drawPileCapacity=131072,initialDrawPileSha256=pile_hash,executableSha256=hashlib.sha256(exe.read_bytes()).hexdigest(),cases=summary)
(out/'summary.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('PASS',len(summary))
