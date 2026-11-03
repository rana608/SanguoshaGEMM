"""Extract the required official offline installer archives without running an installer."""
import mmap, struct, zlib, pathlib, subprocess
root=pathlib.Path(__file__).resolve().parents[1]
parts=root/'.tools/parts'; parts.mkdir(exist_ok=True)
dest=root/'.tools/qt';dest.mkdir(exist_ok=True)
with open(root/'.tools/qt-installer.exe','rb') as f:
    data=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
    at=0;index=0
    while True:
        at=data.find(b'7z\xbc\xaf\x27\x1c',at)
        if at<0:break
        header=data[at:at+32];at+=1
        if len(header)!=32:continue
        crc,off,size,ncrc=struct.unpack('<IQQI',header[8:])
        if zlib.crc32(header[12:])!=crc:continue
        begin=at-1;end=begin+32+off+size
        if end>len(data):continue
        if zlib.crc32(data[begin+32+off:end])!=ncrc:continue
        archive=parts/f'{begin}.7z'
        if not archive.exists():archive.write_bytes(data[begin:end])
        listing=subprocess.check_output(['7z','l','-slt',str(archive)],text=True,errors='replace')
        paths=[l[7:] for l in listing.splitlines() if l.startswith('Path = ')][1:]
        wanted=any('mingw492' in p.lower() for p in paths)
        if wanted:
            print('Extract',archive.name,paths[:3],flush=True)
            subprocess.run(['7z','x','-y',str(archive),f'-o{dest}','-bso0'],check=True)
        else:print('Skip',archive.name,paths[:2],flush=True)
        index+=1;at=end
    print('Valid archives',index)
