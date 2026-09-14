"""Read-only runtime ELF/import audit; run only in the isolated QPP image."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import struct
import subprocess
import time

ROOTS=('/usr','/bin','/sbin','/lib','/lib64','/work','/opt')
LIMIT=240


def linkage_ok(code,text):
    if 'not found' in text:return False
    return code==0 or 'not a dynamic executable' in text or 'statically linked' in text


def main():
    started=time.monotonic();seen=set();files=[];errors=[]
    for root in ROOTS:
        def walk_error(error):errors.append({'path':str(error.filename),'error':type(error).__name__})
        for directory,dirs,names in os.walk(root,followlinks=False,onerror=walk_error):
            for name in names:
                path=Path(directory)/name
                if path.is_symlink():continue
                try:
                    info=path.stat();identity=(info.st_dev,info.st_ino)
                    if identity in seen:continue
                    seen.add(identity)
                    with path.open('rb') as stream:head=stream.read(20)
                    if len(head)<20 or head[:4]!=b'\x7fELF':continue
                    if head[5] not in (1,2):raise ValueError('ELF encoding')
                    kind=struct.unpack('<H' if head[5]==1 else '>H',head[16:18])[0]
                    if kind not in (2,3):continue
                    if len(files)>=2048 or time.monotonic()-started>LIMIT:raise TimeoutError('audit bound')
                    result=subprocess.run(['ldd',str(path)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                          timeout=min(15,max(1,LIMIT-(time.monotonic()-started))))
                    raw=result.stdout
                    if len(raw)>65536:raise ValueError('ldd output bound')
                    text=raw.decode('utf-8',errors='replace')
                    h=hashlib.sha256()
                    with path.open('rb') as stream:
                        while chunk:=stream.read(1024*1024):h.update(chunk)
                    files.append({'path':str(path),'bytes':info.st_size,'sha256':h.hexdigest(),
                                  'elf_type':kind,'ldd_exit_code':result.returncode,'ldd':text,
                                  'linkage_ok':linkage_ok(result.returncode,text)})
                except Exception as error:
                    errors.append({'path':str(path),'error':type(error).__name__})
                    if isinstance(error,TimeoutError):break
            if time.monotonic()-started>LIMIT:break
        if time.monotonic()-started>LIMIT:break
    imports=[]
    for name in ('qristal.core','numpy','scipy.linalg','symengine','qiskit'):
        item={'module':name,'passed':False}
        try:
            module=importlib.import_module(name)
            item.update(passed=True,file=getattr(module,'__file__',None),version=getattr(module,'__version__',None))
        except Exception as error:item['error']=type(error).__name__
        imports.append(item)
    result={'schema':'qb.qpp-image-elf-audit/v1','roots':ROOTS,'elf_files':files,'errors':errors,'imports':imports,
            'passed':bool(files) and not errors and all(f['linkage_ok'] for f in files) and all(i['passed'] for i in imports),
            'elapsed_seconds':round(time.monotonic()-started,2),
            'scope':'runtime and standard OS ELF roots; ldd plus five imports, not every plugin operation or hosted qualification'}
    print('QPP_IMAGE_AUDIT '+json.dumps(result,sort_keys=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
