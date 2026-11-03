"""Download pinned official archives; verify before extracting or executing."""
import hashlib, pathlib, urllib.request, zipfile

root=pathlib.Path(__file__).resolve().parents[1]
dest=root/'.tools';dest.mkdir(exist_ok=True)
downloads=[
    ('qt-installer.exe','https://download.qt.io/archive/qt/5.5/5.5.1/qt-opensource-windows-x86-mingw492-5.5.1.exe',
     'f0e93a33c416a6fb8649cf3891d4ed20444f4e5720328792fa4d07dfa49808d5'),
    ('swig.zip','https://downloads.sourceforge.net/project/swig/swigwin/swigwin-3.0.12/swigwin-3.0.12.zip',
     '21ce6cbe297a56b697ef6e7e92a83e75ca41dedc87e48282ab444591986c35f5'),
]
for name,url,expected in downloads:
    target=dest/name
    if not target.exists():
        partial=dest/(name+'.partial')
        print('Downloading',name,flush=True)
        with urllib.request.urlopen(url,timeout=60) as src,partial.open('wb') as dst:
            while chunk:=src.read(1024*1024):dst.write(chunk)
        partial.replace(target)
    with target.open('rb') as stream:
        digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=expected:raise RuntimeError(f'Unexpected SHA256 for {target}: {digest}')
    print('Verified',name,flush=True)
if not (dest/'swigwin-3.0.12/swig.exe').exists():
    with zipfile.ZipFile(dest/'swig.zip') as archive:
        for member in archive.infolist():
            assert (dest/member.filename).resolve().is_relative_to(dest.resolve())
        archive.extractall(dest)
