"""Freeze a reproducible, deduplicated matrix corpus before measuring performance."""
import hashlib, itertools, json, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parents[1]
SEED = 20261103
FAMILIES = {
    'dense-low': '稠密小数值 1–3',
    'dense-uniform': '稠密均匀 1–9',
    'dense-high': '稠密大数值 7–9',
    'large-left': '左大右小（7–9 × 1–3）',
    'small-left': '左小右大（1–3 × 7–9）',
    'mixed': '均匀含零 0–9',
    'sparse-50': '独立 50% 置零',
    'sparse-75': '独立 75% 置零',
    'boundary': '边界与固定回归',
}

def generate():
    rng = random.Random(SEED)
    candidates = []
    def draw(rows, cols, low, high, zero=0):
        return [[0 if zero and rng.random() < zero else rng.randint(low, high) for _ in range(cols)] for _ in range(rows)]
    def add_random(family, m, k, n, repeat):
        specs = {
            'dense-low': (1,3,1,3,0), 'dense-uniform': (1,9,1,9,0), 'dense-high': (7,9,7,9,0),
            'large-left': (7,9,1,3,0), 'small-left': (1,3,7,9,0), 'mixed': (0,9,0,9,0),
            'sparse-50': (1,9,1,9,.5), 'sparse-75': (1,9,1,9,.75),
        }
        al, ah, bl, bh, zero = specs[family]
        candidates.append(dict(A=draw(m,k,al,ah,zero), B=draw(k,n,bl,bh,zero), family=family,
                               label=f'{family} / {m}x{k}x{n} / {repeat}'))
    for shape in itertools.product([1,2], repeat=3):
        for family in list(FAMILIES)[:-1]: add_random(family, *shape, 0)
    # Additional full 2x2 cases, without selecting for observed speedups.
    for repeat in range(1,4):
        for family in list(FAMILIES)[:-1]: add_random(family, 2,2,2,repeat)
    fixed = [
        ('左零矩阵', [[0,0],[0,0]], [[7,3],[4,9]]),
        ('右零矩阵', [[7,3],[4,9]], [[0,0],[0,0]]),
        ('双方全零', [[0,0],[0,0]], [[0,0],[0,0]]),
        ('双方全9 / 每个结果162张', [[9,9],[9,9]], [[9,9],[9,9]]),
        ('稠密相等循环次数', [[1,2],[3,4]], [[4,3],[2,1]]),
        ('右矩阵整行零', [[8,3],[2,7]], [[0,0],[5,4]]),
        ('右矩阵整列零', [[8,3],[2,7]], [[0,5],[0,4]]),
        ('指定回归样例', [[1,2],[3,0]], [[2,1],[1,2]]),
    ]
    for label,a,b in fixed: candidates.append(dict(A=a,B=b,family='boundary',label=label))
    unique = {}
    for candidate in candidates:
        a,b = candidate['A'],candidate['B']
        key = json.dumps(dict(A=a,B=b),sort_keys=True,separators=(',',':'))
        if key not in unique:
            unique[key] = dict(A=a,B=b,shape=[len(a),len(b),len(b[0])],families=[],labels=[],
                               zeroFractionA=sum(v==0 for r in a for v in r)/sum(map(len,a)),
                               zeroFractionB=sum(v==0 for r in b for v in r)/sum(map(len,b)))
        item = unique[key]
        if candidate['family'] not in item['families']: item['families'].append(candidate['family'])
        item['labels'].append(candidate['label'])
    cases = list(unique.values())
    random.Random(SEED+1).shuffle(cases)
    out = ROOT/'examples/suites/sgemm-v1';out.mkdir(parents=True,exist_ok=True)
    for index,item in enumerate(cases,1):
        item['id'] = f'case-{index:03d}'
        path = out/(item['id']+'.json')
        payload = json.dumps(dict(A=item['A'],B=item['B'],speed=2),sort_keys=True,separators=(',',':'))
        path.write_text(payload,encoding='utf-8')
        item['inputFile'] = path.name
        item['inputSha256'] = hashlib.sha256(payload.encode()).hexdigest()
    catalog = dict(schemaVersion=1,name='sgemm-suite-v1',seed=SEED,orderSeed=SEED+1,
                   candidateCount=len(candidates),uniqueInputs=len(cases),familyLabels=FAMILIES,
                   policy='Generated before timing. Deduplicate exact A/B pairs; keep all family labels. No identity-matrix performance fixture.',cases=cases)
    (out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'{len(candidates)} proposed cases, {len(cases)} unique matrix pairs; all 8 shapes; seed {SEED}')
    return catalog

if __name__=='__main__': generate()
