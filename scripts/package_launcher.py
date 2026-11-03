"""Package the native launcher, and optionally both unchanged edition folders in one ZIP."""
import argparse,hashlib,json,pathlib,re,shutil,subprocess,zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
def copy_file(source,target):
    # An already-open launcher need not be closed when its identical runtime is repackaged.
    if target.exists() and source.read_bytes()==target.read_bytes():return
    shutil.copy2(source,target)
parser=argparse.ArgumentParser();parser.add_argument('--archive',action='store_true');args=parser.parse_args()
qt=ROOT/'.tools/qt/5.5/mingw492_32';dest=ROOT/'dist/SanguoshaGEMM-Launcher'
dest.mkdir(parents=True,exist_ok=True)
copy_file(ROOT/'build/launcher/SanguoshaGEMM-Launcher.exe',dest/'SanguoshaGEMM-Launcher.exe')
pending=[dest/'SanguoshaGEMM-Launcher.exe']
for folder,names in {'platforms':['qwindows.dll','qoffscreen.dll'],'imageformats':['qjpeg.dll','qico.dll']}.items():
    (dest/'plugins'/folder).mkdir(parents=True,exist_ok=True)
    for name in names:
        target=dest/'plugins'/folder/name;copy_file(qt/'plugins'/folder/name,target);pending.append(target)
seen=set();objdump=ROOT/'.tools/qt/Tools/mingw492_32/bin/objdump.exe'
while pending:
    p=pending.pop()
    if p in seen:continue
    seen.add(p)
    info=subprocess.check_output([str(objdump),'-p',str(p)],text=True,errors='replace')
    for name in re.findall(r'DLL Name:\s*(\S+)',info):
        source=qt/'bin'/name
        if source.exists() and dest/name not in seen:
            copy_file(source,dest/name);pending.append(dest/name)
(dest/'qt.conf').write_text('[Paths]\nPrefix=.\nPlugins=plugins\n',encoding='ascii')
(dest/'assets').mkdir(exist_ok=True)
shutil.copy2(ROOT/'upstream/image/system/backdrop/default.jpg',dest/'assets/backdrop.jpg')
shutil.copy2(ROOT/'upstream/resource/icon/sgs.ico',dest/'assets/sgs.ico')
shutil.copytree(ROOT/'licenses',dest/'licenses',dirs_exist_ok=True)
for name in ['LICENSE','GPLv3','MCFR']:shutil.copy2(ROOT/'upstream'/name,dest/name)
shutil.copy2(ROOT/'docs/LAUNCHER.md',dest/'README.md')
print('Launcher ready:',dest)
if args.archive:
    files=[(p,'SanguoshaGEMM/'+p.relative_to(dest).as_posix()) for p in sorted(dest.rglob('*')) if p.is_file()]
    manifest_path=ROOT/'evidence/frozen/current-manifest.json'
    if not manifest_path.exists():manifest_path=ROOT/'evidence/frozen/expanded-v1-manifest.json'
    expected=json.loads(manifest_path.read_text(encoding='utf-8'))['editions']
    for label in ['Baseline','Optimized']:
        folder=ROOT/'dist'/('SanguoshaGEMM-'+label)
        exe=folder/(folder.name+'.exe')
        assert hashlib.sha256(exe.read_bytes()).hexdigest()==expected[label.lower()]['executableSha256']
        files.extend((p,'SanguoshaGEMM/'+folder.name+'/'+p.relative_to(folder).as_posix())
                     for p in sorted(folder.rglob('*')) if p.is_file()
                     and p.name.lower() not in {'config.ini','sanguosha.ini'}
                     and not (p.name.lower().startswith('config-') and p.suffix=='.ini')
                     and 'records' not in p.relative_to(folder).parts)
    path=ROOT/'dist/SanguoshaGEMM-unified-windows.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as archive:
        for source,relative in files:archive.write(source,relative)
    with zipfile.ZipFile(path) as archive:assert archive.testzip() is None
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    manifest=dict(file=path.name,bytes=path.stat().st_size,sha256=digest,
                  launcherSha256=hashlib.sha256((dest/'SanguoshaGEMM-Launcher.exe').read_bytes()).hexdigest(),
                  editions=expected)
    (ROOT/'dist/unified-SHA256.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))
