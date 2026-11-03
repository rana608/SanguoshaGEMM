"""Freeze the larger-value 2x2 corpus before timing either edition."""
import hashlib, json, pathlib, random

ROOT=pathlib.Path(__file__).resolve().parents[1]

def generate():
    out=ROOT/'examples/suites/expanded-v1';out.mkdir(parents=True,exist_ok=True)
    cases=[]
    def add(name,a,b,family):
        payload=json.dumps(dict(A=a,B=b,speed=2),sort_keys=True,separators=(',',':'))
        file=name+'.json';(out/file).write_text(payload,encoding='utf-8')
        cases.append(dict(id=name,A=a,B=b,shape=[2,2,2],families=[family],labels=[name],
                          inputFile=file,inputSha256=hashlib.sha256(payload.encode()).hexdigest(),
                          zeroFractionA=sum(x==0 for row in a for x in row)/4,
                          zeroFractionB=sum(x==0 for row in b for x in row)/4))
    for value in [10,25,50,100]:
        add('all-'+str(value),[[value]*2 for _ in range(2)],[[value]*2 for _ in range(2)],'dense')
    rng=random.Random(20261104)
    for i in range(2):
        a=[[rng.randint(10,100) for _ in range(2)] for _ in range(2)]
        b=[[rng.randint(10,100) for _ in range(2)] for _ in range(2)]
        add('random-'+str(i+1),a,b,'dense')
    a,b=[[100,80],[70,90]],[[10,20],[30,10]]
    add('large-left',a,b,'asymmetric');add('small-left',b,a,'asymmetric')
    add('sparse',[[100,0],[70,60]],[[0,80],[50,0]],'sparse')
    add('zero-right',[[100,80],[70,90]],[[0,0],[0,0]],'zero')
    add('zero-left',[[0,0],[0,0]],[[100,80],[70,90]],'zero')
    add('single-nonzero',[[0,100],[0,0]],[[0,0],[100,0]],'sparse')
    random.Random(20261105).shuffle(cases)
    catalog=dict(schemaVersion=1,name='expanded-v1',seed=20261104,orderSeed=20261105,elementMax=100,
                 candidateCount=len(cases),uniqueInputs=len(cases),cases=cases,
                 familyLabels=dict(dense='稠密与数值阶梯',asymmetric='左右数值不对称',sparse='稀疏',zero='零矩阵边界'))
    (out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Frozen',len(cases),'2x2 inputs, 0..100, including 80000 drawn cards')

if __name__=='__main__':generate()
