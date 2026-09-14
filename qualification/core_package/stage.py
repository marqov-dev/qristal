"""Stage audited native Core inputs without builds, installs or network access."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('core_stage_audit',HERE/'audit.py')
AUDIT=importlib.util.module_from_spec(spec);spec.loader.exec_module(AUDIT)


def snapshot(source,destination,limit,expected=None):
    """Copy one regular, non-symlink file through a fixed descriptor into private storage."""
    source,destination=Path(source),Path(destination)
    fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit:raise ValueError('snapshot file bound/type')
        digest=hashlib.sha256();count=0
        with os.fdopen(os.dup(fd),'rb') as src,destination.open('xb') as dst:
            while chunk:=src.read(1024*1024):
                count+=len(chunk)
                if count>limit:raise ValueError('snapshot byte bound')
                digest.update(chunk);dst.write(chunk)
            dst.flush();os.fsync(dst.fileno())
        after=os.fstat(fd)
        if (before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns) or count!=before.st_size:
            raise ValueError('source changed during snapshot')
        identity={'bytes':count,'sha256':digest.hexdigest()}
        if expected is not None and identity!=expected:raise ValueError('snapshot identity')
        destination.chmod(0o400)
        return identity
    finally:os.close(fd)


class HashReader:
    def __init__(self,source):
        self.source=source;self.digest=hashlib.sha256();self.count=0
    def read(self,size=-1):
        data=self.source.read(size);self.digest.update(data);self.count+=len(data)
        return data


def retain_installs(archive,context,inventory):
    """Preserve Linux case-sensitive paths in a tar payload; never extract on host."""
    selected={name:entry for name,entry in inventory.items() if name.split('/')[0] in ('install-core','install-xacc')}
    AUDIT.OUTPUT.check_links(selected)
    antlr='antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl'
    wanted=dict(selected,**{antlr:inventory[antlr]})
    for name,entry in wanted.items():
        AUDIT.OUTPUT.safe_name(name)
        if entry['mode'] & ~0o777:raise ValueError('staging special mode')
        if entry['type'] not in ('file','directory','symlink'):raise ValueError('staging member type')
        if entry['type']=='symlink':AUDIT.OUTPUT.safe_link(name,entry['target'])
    written=set()
    with tarfile.open(archive,'r|gz') as stream,tarfile.open(context/'work.tar','w',format=tarfile.PAX_FORMAT) as payload:
        for member in stream:
            if member.name not in wanted:continue
            entry=wanted[member.name]
            if member.name in written:raise ValueError('duplicate staging member')
            written.add(member.name)
            if member.mode!=entry['mode']:raise ValueError('staging mode mismatch')
            # Fresh metadata deliberately omits upstream owners and PAX extensions.
            retained=tarfile.TarInfo(member.name);retained.mode=entry['mode']
            if entry['type']=='directory':
                if not member.isdir():raise ValueError('staging directory mismatch')
                retained.type=tarfile.DIRTYPE;payload.addfile(retained);continue
            if entry['type']=='symlink':
                if not member.issym() or member.linkname!=entry['target']:raise ValueError('staging link mismatch')
                retained.type=tarfile.SYMTYPE;retained.linkname=entry['target'];payload.addfile(retained);continue
            if not member.isfile() or member.size!=entry['size']:raise ValueError('staging file mismatch')
            retained.size=entry['size']
            with stream.extractfile(member) as source:
                reader=HashReader(source)
                if member.name==antlr:
                    target=context/'python/wheels'/Path(antlr).name
                    with target.open('xb') as destination:
                        while chunk:=reader.read(1024*1024):
                            if reader.count>entry['size']:raise ValueError('staging file bound')
                            destination.write(chunk)
                        destination.flush();os.fsync(destination.fileno())
                    target.chmod(entry['mode'])
                else:payload.addfile(retained,reader)
            if reader.count!=entry['size'] or reader.digest.hexdigest()!=entry['sha256']:raise ValueError('staging file identity')
    if written!=set(wanted):raise ValueError('missing staging members')
    # Independently read back the serialized payload, binding every member to the
    # already validated original receipt without depending on host path semantics.
    actual={}
    with tarfile.open(context/'work.tar','r|') as stream:
        for member in stream:
            if member.name in actual:raise ValueError('duplicate retained member')
            entry={'mode':member.mode}
            if member.isdir():entry['type']='directory'
            elif member.issym():entry.update(type='symlink',target=member.linkname)
            elif member.isfile():
                with stream.extractfile(member) as source:
                    reader=HashReader(source)
                    while reader.read(1024*1024):pass
                entry.update(type='file',size=reader.count,sha256=reader.digest.hexdigest())
            else:raise ValueError('retained member type')
            actual[member.name]=entry
    if actual!=selected:raise ValueError('retained payload inventory mismatch')
    return selected


def context_inventory(context):
    result={}
    for path in sorted(context.rglob('*')):
        name=path.relative_to(context).as_posix()
        mode=stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():result[name]={'type':'symlink','mode':mode,'target':str(path.readlink())}
        elif path.is_dir():result[name]={'type':'directory','mode':mode}
        elif path.is_file():result[name]={'type':'file','mode':mode,'bytes':path.stat().st_size,'sha256':AUDIT.sha(path)}
        else:raise ValueError('unexpected staged file type')
    return result


def stage(archive,protocol,native_receipt,material_manifest,wheels,output,recovery_verification=None):
    output,wheels=Path(output),Path(wheels)
    if output.exists() or output.is_symlink():raise FileExistsError('new context required')
    if wheels.is_symlink() or not wheels.is_dir():raise ValueError('wheel directory')
    # A private sibling workspace isolates every audited byte from mutable operator inputs.
    with tempfile.TemporaryDirectory(prefix='.core-stage-',dir=output.parent) as temporary:
        private=Path(temporary);snap=private/'snapshot';snap.mkdir()
        sources={'archive.tar.gz':(archive,AUDIT.OUTPUT.MAX_BYTES),'protocol.json':(protocol,2*1024**2),
                 'native-receipt.json':(native_receipt,2*1024**2),'material-manifest.json':(material_manifest,32*1024**2)}
        if recovery_verification is not None:sources['recovery-verification.json']=(recovery_verification,2*1024**2)
        for name,(source,limit) in sources.items():snapshot(source,snap/name,limit)
        plan=AUDIT.audit(snap/'archive.tar.gz',snap/'protocol.json',snap/'native-receipt.json',snap/'material-manifest.json',
                         snap/'recovery-verification.json' if recovery_verification is not None else None)
        required=plan['required_python']['wheels']
        names={item['filename'] for item in required}
        if len(names)!=50 or any(Path(name).name!=name or '\\' in name for name in names):raise ValueError('wheel names')
        if {p.name for p in wheels.iterdir()}!=names:raise ValueError('missing or extra supplied wheel')
        wheel_snap=snap/'wheels';wheel_snap.mkdir()
        for item in required:
            snapshot(wheels/item['filename'],wheel_snap/item['filename'],item['bytes'],
                     {'bytes':item['bytes'],'sha256':item['sha256']})
        if {p.name for p in wheels.iterdir()}!=names:raise ValueError('wheel directory changed')
        context=private/'context';context.mkdir(mode=0o700)
        (context/'python/wheels').mkdir(parents=True)
        work_inventory=retain_installs(snap/'archive.tar.gz',context,plan['retained_inventory'])
        for item in required:
            destination=context/'python/wheels'/item['filename']
            snapshot(wheel_snap/item['filename'],destination,item['bytes'],{'bytes':item['bytes'],'sha256':item['sha256']})
            destination.chmod(0o644)
        evidence=context/'evidence';evidence.mkdir()
        for name in sources:
            if name!='archive.tar.gz':shutil.copyfile(snap/name,evidence/name)
        (evidence/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        recipe_identity=snapshot(HERE/'recipe.py',evidence/'recipe.py',2*1024**2)
        recipe=AUDIT.load('core_stage_recipe',HERE/'recipe.py')
        recipe.attach(context,plan)
        if AUDIT.sha(HERE/'recipe.py')!=recipe_identity['sha256']:raise ValueError('recipe changed during staging')
        result={'schema':'qb.core-staged-inputs/v1','staged':True,'runtime_built':False,'runtime_qualified':False,
                'published':False,'hosted':False,'scope':plan['scope'],'bindings':plan['bindings'],
                'stage_sha256':AUDIT.sha(__file__),'recipe_sha256':recipe_identity['sha256'],
                'inventory':context_inventory(context),'evidence_provenance':plan['evidence_provenance'],
                'wheel_count':len(required)+1,'work_inventory':work_inventory,
                'layout':{'work_archive':'work.tar','archive_roots':['install-core','install-xacc'],
                          'linux_unpack_destination':'/work','wheels':'python/wheels'}}
        (context/'staging.json').write_text(json.dumps(result,indent=2)+'\n')
        # Reserve exclusively; never replace a pre-existing user directory.
        output.mkdir(mode=0o700)
        try:os.replace(context,output)
        except Exception:
            output.rmdir()
            raise
        return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','protocol','native_receipt','material_manifest','wheels','output'):parser.add_argument(name,type=Path)
    parser.add_argument('--recovery-verification',type=Path)
    args=parser.parse_args()
    print(json.dumps(stage(**vars(args)),indent=2))

if __name__=='__main__':main()
