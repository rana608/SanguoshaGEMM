"""Copy browsable suite reports without duplicating all engine traces in each runtime."""
import pathlib, shutil

ROOT=pathlib.Path(__file__).resolve().parents[1]

def export(source,dest,historical=False):
    for p in source.rglob('*'):
        if p.is_file() and p.name in {'report.html','summary.json','summary.csv','catalog.json'}:
            target=dest/p.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            if historical and p.name=='report.html':
                content=p.read_text(encoding='utf-8')
                banner='<p style="padding:14px;border:1px solid #b58a42;background:#fff3cd;color:#47381e">历史测量：此报告对应旧程序及资源配置，不代表当前统一大牌堆版的耗时。请以报告中的程序哈希为准；新计时需重新运行。</p>'
                content=content.replace('<main>','<main>'+banner,1)
                target.write_text(content,encoding='utf-8')
            else:shutil.copy2(p,target)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('source',type=pathlib.Path);parser.add_argument('destination',type=pathlib.Path);parser.add_argument('--historical',action='store_true')
    args=parser.parse_args();export(args.source,args.destination,args.historical)
