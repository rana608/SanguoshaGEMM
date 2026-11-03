"""Compare both native executables on one input, in turbo mode, without desktop automation."""
import argparse, datetime, hashlib, html, json, math, os, pathlib, statistics, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
EDITIONS = {'baseline': 'baseline-v1', 'optimized': 'transpose-v1.2'}

def executable(edition):
    name = 'SanguoshaGEMM-' + edition.title()
    for base in [ROOT / 'dist', ROOT]:
        candidate = base / name / (name + '.exe')
        if candidate.exists(): return candidate
    raise FileNotFoundError('Cannot find ' + name + '.exe; pass its path explicitly')

def timestamp():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%d-%H%M%S-%f')

def matrix(value):
    return '<table class="matrix">' + ''.join('<tr>' + ''.join('<td>' + html.escape(str(x)) + '</td>' for x in row) + '</tr>' for row in value) + '</table>'

def render(s):
    left, right = s['results']
    ratio=right['speedupVsBaseline']
    ratio_text=f'{ratio:.2f}×' if ratio is not None else '不适用（存在零结算时间，见完整计算用时）'
    metrics = [('引擎结算中位数','medianMs','ms'),('引擎结算 p95','p95Ms','ms'),
               ('局面准备＋完整结算中位数','medianComputeMs','ms'),('含程序启动的总用时中位数','medianProcessWallMs','ms'),
               ('主动出杀次数','activeCardUses','次'),('救援 / 放逐次数','rescues','次'),
               ('实际摸牌数量','drawnCards','张'),('进程工作集峰值','peakWorkingSetMiB','MiB')]
    rows=[]
    for label,key,unit in metrics:
        values=[f'{r[key]:.2f}' if unit in ('ms','MiB') else str(r[key]) for r in [left,right]]
        rows.append(f'<tr><th>{label}</th><td>{values[0]} {unit}</td><td>{values[1]} {unit}</td></tr>')
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>三国杀 GEMM · 极速对比</title><style>
body{font-family:"Microsoft YaHei",system-ui,sans-serif;background:#f3f5f7;color:#182128;margin:0;padding:32px 18px;line-height:1.65}main{max-width:980px;margin:auto}h1{font-size:30px;margin:0}h2{font-size:19px}p{color:#52616c}.badge{display:inline-block;background:#deeee4;color:#1b6241;padding:4px 12px;border-radius:5px}.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:24px 0}.card,section{background:white;border:1px solid #dfe5e8;border-radius:10px;padding:22px}.card strong{display:block;font-size:42px;line-height:1.3}.optimized{border-top:4px solid #23734e}.baseline{border-top:4px solid #657786}.inputs{display:flex;align-items:center;gap:22px;flex-wrap:wrap}.matrix{border-left:2px solid #687881;border-right:2px solid #687881;margin:8px 0}.matrix td{padding:2px 15px;text-align:right;font-family:Consolas,monospace}.metrics{width:100%;border-collapse:collapse}.metrics th,.metrics td{padding:12px 8px;border-bottom:1px solid #e6ebee;text-align:right}.metrics th:first-child{text-align:left}.metrics thead{color:#536875}.note{font-size:13px;overflow-wrap:anywhere}a{color:#1d6949}section{margin:18px 0}@media(max-width:600px){.cards{grid-template-columns:1fr}.card strong{font-size:34px}.metrics{font-size:13px}}
</style><main><h1>三国杀 GEMM · 极速对比</h1><p>同一份矩阵输入 · 两个独立程序 · 均为极速模式</p><span class="badge">两版结果一致，已通过独立整数核验</span>
<section><div class="inputs"><div>A''' + matrix(s['A']) + '</div><b>×</b><div>B' + matrix(s['B']) + '</div><b>=</b><div>C' + matrix(s['C']) + '''</div></div></section>
<div class="cards"><div class="card baseline"><h2>原始无优化版</h2><strong>''' + f'{left["medianMs"]:.2f} ms' + '''</strong><p>引擎结算中位数 · baseline-v1</p></div><div class="card optimized"><h2>优化版</h2><strong>''' + f'{right["medianMs"]:.2f} ms' + '''</strong><p>引擎结算中位数 · 跳过零项＋选择方向</p></div></div>
<section><h2>本次引擎结算加速比：''' + ratio_text + '''</h2><table class="metrics"><thead><tr><th>指标</th><th>原始无优化版</th><th>优化版</th></tr></thead><tbody>''' + ''.join(rows) + '''</tbody></table></section>
<p>每版 ''' + str(s['warmupRuns']) + ' 次预热，' + str(s['measuredRuns']) + ''' 次实测；按轮次交替先后顺序，串行执行，避免两个程序互相争抢 CPU。数值是本机实测，不保证优化对所有矩阵都更快。</p>
<p class="note">大字指标仅包含实际出牌的引擎结算，排除启动、局面准备、演示等待和渲染。完整计算与含启动时间单列；均强制 speed=2，后台无牌桌渲染。没有 GPU 利用率数据。</p><p class="note">共同输入 SHA256：''' + s['inputSha256'] + '''</p><p><a href="summary.json">查看原始统计 JSON</a></p></main></html>'''

def run_comparison(input_file, output_dir, runs=10, baseline=None, optimized=None):
    if not 1 <= runs <= 100: raise ValueError('Measured runs must be between 1 and 100')
    out=pathlib.Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    try:
        input_text=pathlib.Path(input_file).read_text(encoding='utf-8-sig')
    finally:
        for name in ['summary.json','report.html']:(out/name).unlink(missing_ok=True)
    supplied=json.loads(input_text)
    shared=dict(A=supplied['A'],B=supplied['B'],speed=2)
    payload=json.dumps(shared,sort_keys=True,separators=(',',':')).encode('utf-8')
    input_path=out/'input.json';input_path.write_bytes(payload)
    binaries={'baseline':pathlib.Path(baseline) if baseline else executable('baseline'),
              'optimized':pathlib.Path(optimized) if optimized else executable('optimized')}
    binaries={k:p.resolve(strict=True) for k,p in binaries.items()}
    samples={key:[] for key in EDITIONS};last={}
    for iteration in range(runs+1):
        order=['baseline','optimized'] if iteration%2==0 else ['optimized','baseline']
        for edition in order:
            result=out/f'{edition}-{iteration}.json';result.unlink(missing_ok=True)
            start=time.perf_counter()
            process=subprocess.run([str(binaries[edition]),'--gemm-case',str(input_path),str(result)],cwd=binaries[edition].parent,
                                   env=dict(os.environ,QT_QPA_PLATFORM='offscreen'),capture_output=True,timeout=60)
            process_ms=(time.perf_counter()-start)*1000
            if process.returncode or not result.exists():
                detail=result.read_text(encoding='utf-8') if result.exists() else process.stderr.decode(errors='replace')
                raise RuntimeError(f'{edition} failed ({process.returncode}): {detail}')
            r=json.loads(result.read_text(encoding='utf-8'))
            assert r['edition']==edition and r['algorithm']==EDITIONS[edition] and r['speed']==2
            assert r['A']==shared['A'] and r['B']==shared['B'] and r['status']=='complete'
            oracle=[[sum(x*y for x,y in zip(row,col)) for col in zip(*shared['B'])] for row in shared['A']]
            assert r['C']==oracle
            r['processWallMs']=process_ms;r['computeMs']=r['prepareMs']+r['runWallMs']
            if iteration:samples[edition].append(r)
            last[edition]=r
    rows=[]
    for edition in EDITIONS:
        data,r=samples[edition],last[edition]
        row=dict(edition=edition,algorithm=EDITIONS[edition],samplesMs=[s['engineMs'] for s in data],
                 medianMs=statistics.median(s['engineMs'] for s in data),p95Ms=sorted(s['engineMs'] for s in data)[math.ceil(.95*runs)-1],
                 medianPrepareMs=statistics.median(s['prepareMs'] for s in data),medianRunWallMs=statistics.median(s['runWallMs'] for s in data),
                 medianComputeMs=statistics.median(s['computeMs'] for s in data),medianProcessWallMs=statistics.median(s['processWallMs'] for s in data),
                 medianProcessCpuMs=statistics.median(s['processCpuMs'] for s in data),peakWorkingSetBytes=max(s['peakWorkingSetBytes'] for s in data),
                 processWallSamplesMs=[s['processWallMs'] for s in data],computeSamplesMs=[s['computeMs'] for s in data])
        for key in ['activeCardUses','rescues','fangzhu','drawnCards','judgements','consumedCards']:row[key]=r[key]
        row['transposed']=r['transposed']
        row['peakWorkingSetMiB']=row['peakWorkingSetBytes']/1024**2
        row['executableSha256']=hashlib.sha256(binaries[edition].read_bytes()).hexdigest()
        rows.append(row)
    for row in rows:row['speedupVsBaseline']=rows[0]['medianMs']/row['medianMs'] if rows[0]['medianMs']>0 and row['medianMs']>0 else None
    summary=dict(schemaVersion=1,A=shared['A'],B=shared['B'],C=last['baseline']['C'],speed=2,inputSha256=hashlib.sha256(payload).hexdigest(),
                 createdShanghai=timestamp(),warmupRuns=1,measuredRuns=runs,p95Method='nearest-rank',order='alternating; sequential processes',
                 timing='engineMs excludes startup, setup, intentional delays and rendering; computeMs=setup+runWallMs; processWallMs includes startup and output',results=rows)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'report.html').write_text(render(summary),encoding='utf-8')
    for row in rows:print(f"{row['edition']}: {row['medianMs']:.2f} ms engine median; {row['activeCardUses']} Slash")
    print(out/'report.html')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=pathlib.Path)
    parser.add_argument('--runs',type=int,default=10);parser.add_argument('--output-dir',type=pathlib.Path)
    parser.add_argument('--baseline',type=pathlib.Path);parser.add_argument('--optimized',type=pathlib.Path);args=parser.parse_args()
    run_comparison(args.input,args.output_dir or ROOT/'comparisons'/timestamp(),args.runs,args.baseline,args.optimized)
