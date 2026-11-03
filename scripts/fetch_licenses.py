"""Preserve notices from the exact upstream releases used by this build."""
import concurrent.futures, hashlib, json, pathlib, shutil, urllib.request

root=pathlib.Path(__file__).resolve().parents[1]
dest=root/'licenses'
sources={}
for name in ['LGPL_EXCEPTION.txt','LICENSE.FDL','LICENSE.GPLv3','LICENSE.LGPLv21','LICENSE.LGPLv3']:
    sources['qt/'+name]='https://raw.githubusercontent.com/qt/qtbase/v5.5.1/'+name
sources['freetype/FTL.TXT']='https://raw.githubusercontent.com/freetype/freetype/VER-2-5-5/docs/FTL.TXT'
sources['freetype/GPLv2.TXT']='https://raw.githubusercontent.com/freetype/freetype/VER-2-5-5/docs/GPLv2.TXT'
sources['qt/ANGLE-LICENSE']='https://raw.githubusercontent.com/qt/qtbase/v5.5.1/src/3rdparty/angle/LICENSE'

def fetch(item):
    name,url=item
    path=dest/name
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(url,timeout=60) as response:path.write_bytes(response.read())
    data=path.read_bytes()
    assert len(data)>100 and b'<html' not in data[:200].lower(), name
    return dict(path=name,url=url,sha256=hashlib.sha256(data).hexdigest())

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    manifest=list(pool.map(fetch,sources.items()))
mingw=root/'.tools/qt/Tools/mingw492_32/licenses'
for name in ['gcc','mingw-w64','winpthreads']:
    shutil.copytree(mingw/name,dest/'mingw'/name,dirs_exist_ok=True)
lua=(root/'upstream/src/lua/lua.h').read_text(encoding='utf-8-sig')
begin=lua.index('Copyright (C)')
# Preserve the complete source header, including the MIT license near its end.
(dest/'Lua-lua.h').write_text(lua,encoding='utf-8')
(dest/'sources.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Preserved',len(manifest),'downloaded notices plus bundled Lua/MinGW notices')
