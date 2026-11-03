"""Run one supplied JSON input invisibly and print actual engine results."""
import argparse,datetime,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('input',type=pathlib.Path);p.add_argument('--edition',choices=['baseline','optimized'],default='baseline');p.add_argument('--output',type=pathlib.Path);args=p.parse_args()
if args.output is None:args.output=root/'evidence'/args.edition/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
args.output.parent.mkdir(parents=True,exist_ok=True)
runtime=root/('dist/SanguoshaGEMM-'+args.edition.title())
args.output.unlink(missing_ok=True)
run=subprocess.run([str(runtime/('SanguoshaGEMM-'+args.edition.title()+'.exe')),'--gemm-case',str(args.input.resolve()),str(args.output.resolve())],cwd=runtime,capture_output=True,timeout=600)
if not args.output.exists():sys.exit(f'Engine failed ({run.returncode}): {run.stderr.decode(errors="replace")}')
r=json.loads(args.output.read_text(encoding='utf-8'));print(json.dumps({k:r.get(k) for k in ['status','edition','algorithm','C','activeCardUses','rescues','fangzhu','engineMs','error']},ensure_ascii=False,indent=2))
print(args.output.resolve());sys.exit(run.returncode)
