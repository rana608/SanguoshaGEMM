"""Resolve MinGW/Qt DLL imports without relying on installer-patched build paths."""
import argparse,pathlib,re,shutil,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--edition',choices=['baseline','optimized'],required=True);args=parser.parse_args()
label=args.edition.title()
qt=root/'.tools/qt/5.5/mingw492_32';dest=root/('dist/SanguoshaGEMM-'+label)
objdump=root/'.tools/qt/Tools/mingw492_32/bin/objdump.exe'
pending=[dest/('SanguoshaGEMM-'+label+'.exe')]
for folder,names in {'platforms':['qwindows.dll','qoffscreen.dll','qminimal.dll'],
                     'imageformats':['qjpeg.dll','qgif.dll','qico.dll','qsvg.dll'],
                     'iconengines':['qsvgicon.dll']}.items():
    (dest/'plugins'/folder).mkdir(parents=True,exist_ok=True)
    for name in names:
        src=qt/'plugins'/folder/name
        if src.exists():
            target=dest/'plugins'/folder/name
            shutil.copy2(src,target);pending.append(target)
# animation.qml imports only QtQuick 1.0, registered by Qt5Declarative itself.
# Do not deploy QtWebKit or debug QML plugins and their large dependency trees.
for name in ['libgcc_s_dw2-1.dll','libstdc++-6.dll','libwinpthread-1.dll','libEGL.dll','libGLESv2.dll']:
    shutil.copy2(qt/'bin'/name,dest/name)
    pending.append(dest/name)
seen=set()
while pending:
    p=pending.pop()
    if p in seen:continue
    seen.add(p)
    output=subprocess.check_output([str(objdump),'-p',str(p)],text=True,errors='replace')
    for name in re.findall(r'DLL Name:\s*(\S+)',output):
        src=qt/'bin'/name
        if src.exists() and dest/name not in seen:
            shutil.copy2(src,dest/name);pending.append(dest/name)
# Remove only obsolete generated Qt files within this runtime directory.
runtime_root=dest.resolve()
for p in [*dest.glob('*.dll'),*(dest/'imports').rglob('*')]:
    if not p.is_file():continue
    assert p.resolve().is_relative_to(runtime_root)
    if p not in seen and ((qt/'bin'/p.name).exists() or (dest/'imports') in p.parents):
        p.unlink()
(dest/'qt.conf').write_text('[Paths]\nPrefix=.\nPlugins=plugins\nImports=imports\n',encoding='ascii')
print('Deployed Qt runtime',len(seen),'binaries')
