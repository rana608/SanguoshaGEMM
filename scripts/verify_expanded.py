"""Check actual card identities, resource isolation and both algorithms in the expanded corpus."""
import json, pathlib
from verify_suite import verify

ROOT=pathlib.Path(__file__).resolve().parents[1]
folder=ROOT/'evidence/expanded/suite-v1'
catalog=ROOT/'examples/suites/expanded-v1/catalog.json'
result=verify(folder,catalog)
for case in json.loads(catalog.read_text(encoding='utf-8'))['cases']:
    a,b=case['A'],case['B']
    direct=sum(a[i][k] for i in range(2) for j in range(2) for k in range(2) if b[k][j])
    transposed=sum(b[k][j] for i in range(2) for j in range(2) for k in range(2) if a[i][k])
    for edition in ['baseline','optimized']:
        for record in (folder/'cases'/case['id']).glob(edition+'-*.json'):
            r=json.loads(record.read_text(encoding='utf-8'))
            assert r['resourceVersion']=='expanded-v1'
            assert r['drawPileCapacity']==131072 and r['attackCapacity']==r['rescueCapacity']==800
            assert len(r['initialDrawPile'])==len(set(r['initialDrawPile']))==131072
            expected=2*sum(map(sum,a)) if edition=='baseline' else min(direct,transposed)
            assert r['tasks']==expected
            assert r['transposed']==(edition=='optimized' and transposed<direct)
            initial={p['id']:p for p in r['initialPlayers']}
            slash=set(r['initialPlayers'][0]['hand']);rescue=set(r['initialPlayers'][1]['hand']);pile=set(r['initialDrawPile'])
            assert len(slash)==expected and len(rescue)==800
            assert slash.isdisjoint(rescue) and pile.isdisjoint(slash|rescue)
            seen=set();seen_slash=set();seen_rescue=set();hands={}
            for t in r['trace']:
                ids=set(t['drawnCardIds']);red=set(t['rescueCardIds'])
                assert len(ids)==len(t['drawnCardIds']) and ids<=pile and ids.isdisjoint(seen)
                assert len(ids)==initial[t['target']]['maxhp']-1
                assert len(red)==1 and red<=rescue and red.isdisjoint(seen_rescue)
                assert t['slashId'] in slash and t['slashId'] not in seen_slash
                assert t['before']==hands.get(t['output'],0)
                hands[t['output']]=t['after']
                seen.update(ids);seen_slash.add(t['slashId']);seen_rescue.update(red)
            assert len(seen)==r['drawnCards']
result.update(fixedReserve=131072,attackCapacity=800,rescueCapacity=800,distinctCardIdentities=True,
              taskSchedulesChecked=True,maxOutputPerPlayer=20000,maxDrawnPerCase=80000)
(folder/'integrity.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
