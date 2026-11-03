"""Run a frozen matrix corpus through both native turbo executables and report every result."""
import argparse, csv, hashlib, html, json, pathlib, statistics, sys, time
from compare import ROOT, executable, run_comparison, timestamp

def read(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)

def classify(ratio):
    if ratio < .95: return 'slower'
    if ratio > 1.05: return 'faster'
    return 'similar'

def summarize(catalog,results,meta):
    passed=[r for r in results if r['status']=='passed']
    groups=[]
    def group(name,kind,items):
        if not items:return
        ratios=[r['computeSpeedup'] for r in items]
        groups.append(dict(name=name,kind=kind,count=len(items),medianComputeSpeedup=statistics.median(ratios),
                           faster=sum(r>1.05 for r in ratios),similar=sum(.95<=r<=1.05 for r in ratios),slower=sum(r<.95 for r in ratios),
                           sameSlashCount=sum(r['baseline']['activeCardUses']==r['optimized']['activeCardUses'] for r in items)))
    for family,label in catalog['familyLabels'].items():group(label,'family',[r for r in passed if family in r['families']])
    for shape in sorted({tuple(c['shape']) for c in catalog['cases']}):
        group(' × '.join(map(str,shape)),'shape',[r for r in passed if tuple(r['shape'])==shape])
    ratios=[r['computeSpeedup'] for r in passed]
    return dict(schemaVersion=1,run=meta,status='complete' if len(results)==len(catalog['cases']) else 'running',
                candidateCount=catalog['candidateCount'],uniqueInputs=len(catalog['cases']),completed=len(results),passed=len(passed),
                failed=len(results)-len(passed),faster=sum(r>1.05 for r in ratios),similar=sum(.95<=r<=1.05 for r in ratios),
                slower=sum(r<.95 for r in ratios),groups=groups,cases=results,familyLabels=catalog['familyLabels'])

def write_reports(out,s):
    dump(out/'summary.json',s)
    columns=['id','status','families','shape','A','B','C','baselineEngineMs','optimizedEngineMs','engineSpeedup',
             'baselineComputeMs','optimizedComputeMs','computeSpeedup','baselineProcessMs','optimizedProcessMs',
             'baselineSlash','optimizedSlash','transposed','zeroFractionA','zeroFractionB','error']
    with (out/'summary.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for r in s['cases']:
            row={k:r.get(k,'') for k in columns}
            for k in ['families','shape','A','B','C']:
                row[k]=json.dumps(row[k],ensure_ascii=False,separators=(',',':'))
            if r['status']=='passed':
                b,o=r['baseline'],r['optimized']
                row.update(baselineEngineMs=b['medianMs'],optimizedEngineMs=o['medianMs'],baselineComputeMs=b['medianComputeMs'],
                           optimizedComputeMs=o['medianComputeMs'],baselineProcessMs=b['medianProcessWallMs'],optimizedProcessMs=o['medianProcessWallMs'],
                           baselineSlash=b['activeCardUses'],optimizedSlash=o['activeCardUses'],transposed=o['transposed'])
            writer.writerow(row)
    esc=lambda value:html.escape(str(value),quote=True)
    group_rows=[]
    for g in s['groups']:
        group_rows.append(f'<tr><th>{esc(g["name"])}</th><td>{g["count"]}</td><td>{g["medianComputeSpeedup"]:.2f}×</td><td>{g["faster"]} / {g["similar"]} / {g["slower"]}</td><td>{g["sameSlashCount"]}</td></tr>')
    rows=[]
    for r in s['cases']:
        families=' / '.join(s['familyLabels'][f] for f in r['families'])
        cells=f'<td>{esc(r["id"])}</td><td>{esc(families)}<br>{esc(" × ".join(map(str,r["shape"])))}</td>'
        cells+='<td><code>A='+esc(json.dumps(r['A'],separators=(',',':')))+'<br>B='+esc(json.dumps(r['B'],separators=(',',':')))+'<br>C='+esc(json.dumps(r.get('C'),separators=(',',':')))+ '</code></td>'
        category='failed'
        if r['status']=='passed':
            b,o=r['baseline'],r['optimized'];category=classify(r['computeSpeedup'])
            engine='—（零结算）' if r['engineSpeedup'] is None else f'{r["engineSpeedup"]:.2f}×'
            cells+=f'<td>{b["medianMs"]:.2f} / {o["medianMs"]:.2f}<br>{engine}</td><td>{b["medianComputeMs"]:.2f} / {o["medianComputeMs"]:.2f}<br><b>{r["computeSpeedup"]:.2f}×</b></td>'
            cells+=f'<td>{b["medianProcessWallMs"]:.2f} / {o["medianProcessWallMs"]:.2f}</td><td>{b["activeCardUses"]} → {o["activeCardUses"]}</td><td>{"转置" if o["transposed"] else "直接"}</td>'
            cells+=f'<td><a href="cases/{r["id"]}/report.html">逐次数据</a></td>'
        else:cells+='<td colspan="6">失败：'+esc(r['error'])+'</td>'
        rows.append(f'<tr class="{category}" data-kind="{category}" data-families="{esc(" ".join(r["families"]))}">{cells}</tr>')
    options=''.join('<option value="'+esc(f)+'">'+esc(name)+'</option>' for f,name in s['familyLabels'].items())
    content='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>三国杀 GEMM · 多测试集极速对比</title><style>
body{font-family:"Microsoft YaHei",system-ui,sans-serif;margin:0;background:#f4f6f8;color:#1a2832;line-height:1.6}main{max-width:1500px;margin:auto;padding:28px 20px}h1{margin:0;font-size:29px}h2{font-size:20px}p{color:#526270}.cards{display:flex;gap:12px;flex-wrap:wrap}.card,section{border:1px solid #dce3e8;background:white;padding:20px;border-radius:9px;margin:16px 0}.card{flex:1;min-width:130px}.card b{display:block;font-size:30px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:11px 9px;border-bottom:1px solid #e3e8ed;text-align:right;vertical-align:top}th:first-child,td:first-child,td:nth-child(2),td:nth-child(3){text-align:left}thead{background:#eaf0f4}code{white-space:nowrap;font-family:Consolas,monospace}.slower{background:#fff0ec}.faster{background:#f0f8f2}.failed{background:#ffdfdf}input,select{font:inherit;padding:8px;border:1px solid #bcc9d2;border-radius:5px;margin:4px}a{color:#1f634a}.note{font-size:13px}.controls{position:sticky;top:0;background:white;padding:8px 0;z-index:1}
</style><main><h1>三国杀 GEMM · 多测试集极速对比</h1><p>两个独立程序 · 相同矩阵 · speed=2 · 固定输入与随机种子 · 全部结果逐例展示</p>'''
    content+=f'<div class="cards"><div class="card">唯一输入<b>{s["uniqueInputs"]}</b></div><div class="card">结果正确<b>{s["passed"]} / {s["completed"]}</b></div><div class="card">完整计算用时<br>较快 / 接近 / 较慢<b>{s["faster"]} / {s["similar"]} / {s["slower"]}</b></div></div>'
    content+=f'<p>当前状态：{s["status"]}；失败 {s["failed"]} 例。每例每版预热 1 次、实测 {s["run"]["runs"]} 次，交替先后顺序并串行执行。三维尺寸记为 m × k × n；A 为 m × k，B 为 k × n。</p>'
    content+='<section><h2>计时与统计口径</h2><p>分类和分组倍数使用“局面准备＋完整结算”的中位数之比；大于 1 表示优化版更快。±5% 记为接近，这是展示分档，不是统计显著性检验。引擎纯结算与含启动总时间分别列出。零结算时间的引擎倍数记为不适用，不填成 1× 或无穷大。</p><p>此合成测试集限于当前支持的维度 1–2、整数 0–9；不代表大矩阵或 BLAS 性能。稀疏类别使用逐元素置零概率，具体零元素比例见 JSON/CSV。相同 A/B 输入去重，保留多个类别标签；分组计数可能重叠。输入在测量前固定，没有根据耗时筛选。</p>'
    content+='<p><a href="summary.json">完整 JSON</a> · <a href="summary.csv">CSV 表格</a> · <a href="catalog.json">测试集和输入</a></p></section>'
    content+='<section><h2>按数值分布与尺寸分组</h2><div class="scroll"><table><thead><tr><th>分组</th><th>用例数</th><th>完整计算倍数中位数</th><th>快 / 接近 / 慢</th><th>出杀次数不变</th></tr></thead><tbody>'+''.join(group_rows)+'</tbody></table></div></section>'
    content+='<section><h2>逐例结果（时间单位 ms；原始版 / 优化版）</h2><div class="controls"><input id="search" aria-label="搜索输入" placeholder="搜索编号或矩阵数字"><select id="family" aria-label="筛选类别"><option value="">全部类别</option>'+options+'</select><select id="kind" aria-label="筛选速度"><option value="">全部快慢结果</option><option value="slower">优化版较慢</option><option value="similar">接近</option><option value="faster">优化版较快</option><option value="failed">失败</option></select><span id="count"></span></div>'
    content+='<div class="scroll"><table id="cases"><thead><tr><th>编号</th><th>类别 / 尺寸</th><th>实际输入与结果</th><th>引擎结算</th><th>准备＋完整结算</th><th>含启动总时间</th><th>出杀数</th><th>优化方向</th><th>记录</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section>'
    content+='''<script>const rows=[...document.querySelectorAll('#cases tbody tr')],q=document.getElementById('search'),f=document.getElementById('family'),k=document.getElementById('kind');function filter(){let n=0;for(const r of rows){const visible=r.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!f.value||r.dataset.families.split(' ').includes(f.value))&&(!k.value||r.dataset.kind===k.value);r.hidden=!visible;if(visible)n++}document.getElementById('count').textContent='显示 '+n+' 例'}[q,f,k].forEach(x=>x.addEventListener('input',filter));filter();</script></main></html>'''
    (out/'report.html').write_text(content,encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=pathlib.Path)
    parser.add_argument('--output-dir',type=pathlib.Path)
    parser.add_argument('--runs',type=int,default=10)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--baseline',type=pathlib.Path);parser.add_argument('--optimized',type=pathlib.Path)
    args=parser.parse_args()
    if not 1<=args.runs<=100:parser.error('--runs must be 1..100')
    local=pathlib.Path(__file__).resolve().parent
    catalog_path=args.catalog or (ROOT/'examples/suites/sgemm-v1/catalog.json' if (ROOT/'examples').exists() else local/'examples/suites/sgemm-v1/catalog.json')
    catalog=read(catalog_path)
    binaries={e:p.resolve() for e,p in dict(baseline=args.baseline or executable('baseline'),optimized=args.optimized or executable('optimized')).items()}
    out=(args.output_dir or ROOT/'suite-results'/timestamp()).resolve();out.mkdir(parents=True,exist_ok=True)
    for case in catalog['cases']:
        assert digest(catalog_path.parent/case['inputFile'])==case['inputSha256'],case['id']
    meta=dict(catalogSha256=digest(catalog_path),runs=args.runs,warmupRuns=1,speed=2,seed=catalog['seed'],
              executableSha256={e:digest(p) for e,p in binaries.items()},
              runnerSha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()+(local/'compare.py').read_bytes()).hexdigest(),
              createdShanghai=timestamp())
    results=[]
    if args.resume and (out/'summary.json').exists():
        previous=read(out/'summary.json')
        for key in ['catalogSha256','runs','executableSha256','runnerSha256']:
            if previous['run'][key]!=meta[key]:raise ValueError('Cannot resume different input/binary/methodology: '+key)
        results=previous['cases'];meta=previous['run']
    elif (out/'summary.json').exists():
        raise ValueError('Output already contains results; choose another directory or --resume')
    method=out/'method';method.mkdir(exist_ok=True)
    for name in ['benchmark_suite.py','compare.py']:
        (method/name).write_bytes((local/name).read_bytes())
    dump(out/'catalog.json',catalog)
    finished={r['id'] for r in results}
    summary=summarize(catalog,results,meta)
    write_reports(out,summary)
    for case in catalog['cases']:
        if case['id'] in finished:continue
        print(f'START {len(results)+1}/{len(catalog["cases"])} {case["id"]} {case["families"]}',flush=True)
        row={k:case[k] for k in ['id','A','B','shape','families','labels','zeroFractionA','zeroFractionB']}
        try:
            s=run_comparison(catalog_path.parent/case['inputFile'],out/'cases'/case['id'],args.runs,**binaries)
            assert s['inputSha256']==case['inputSha256']
            b,o=s['results']
            assert b['executableSha256']==meta['executableSha256']['baseline'] and o['executableSha256']==meta['executableSha256']['optimized']
            row.update(status='passed',C=s['C'],baseline=b,optimized=o,engineSpeedup=o['speedupVsBaseline'],computeSpeedup=b['medianComputeMs']/o['medianComputeMs'])
        except Exception as error:
            row.update(status='failed',error=str(error))
            print('FAILED',case['id'],error,flush=True)
        results.append(row)
        summary=summarize(catalog,results,meta);write_reports(out,summary)
    print(f'FINISHED {summary["passed"]}/{summary["uniqueInputs"]} passed, {summary["failed"]} failed: {out/"report.html"}',flush=True)
    return 1 if summary['failed'] else 0

if __name__=='__main__':sys.exit(main())
