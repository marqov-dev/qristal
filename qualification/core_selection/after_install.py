"""Audit the XACC derivative after Core installation and link normalization."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

PLUGINS={'qb_gateset_transpiler','qb_qobj_compiler','algorithm_ae','algorithm_es',
         'aws_braket','circuits','sparse_simulator','uccsd','vqe'}


def inventory(root):
    spec=importlib.util.spec_from_file_location('postinstall_inventory',
        Path(__file__).resolve().parent.parent/'core_native/verify_materials.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    # Original XACC links stay internal. New normalized Core links intentionally
    # cross to its sibling prefix and are checked separately, never dereferenced here.
    return module.inventory(root)


def original_entries(inputs):
    inputs=Path(inputs)
    archive_path=inputs/'xacc/archive.tar.gz'
    report=json.loads((inputs/'xacc/recovered.json').read_text())
    report=report.get('result',report)
    expected=report['output_artifact']
    if archive_path.is_symlink() or archive_path.stat().st_size!=expected['bytes']:
        raise ValueError('baseline archive size/type')
    digest=hashlib.sha256()
    with archive_path.open('rb') as stream:
        while data:=stream.read(1024*1024):digest.update(data)
    if digest.hexdigest()!=expected['sha256']:raise ValueError('baseline archive hash')
    with tarfile.open(archive_path,'r:gz') as archive:
        member=archive.getmember('receipt.json')
        if not member.isfile() or member.size>16*1024*1024:raise ValueError('baseline receipt type/size')
        raw=archive.extractfile(member).read()
    if hashlib.sha256(raw).hexdigest()!=expected['receipt_sha256']:raise ValueError('baseline receipt hash')
    receipt=json.loads(raw)
    if receipt.get('schema')!='qb.source-artifact/v1':raise ValueError('baseline receipt schema')
    result={}
    for name,entry in receipt['entries'].items():
        if not name.startswith('install-xacc/'):continue
        name=name[len('install-xacc/'):]
        if entry['type']=='symlink':result[name]={'type':'link','target':entry['target']}
        elif entry['type']=='directory':result[name]={'type':'directory','mode':entry['mode']}
        elif entry['type']=='file':result[name]={'type':'file','mode':entry['mode'],'bytes':entry['size'],'sha256':entry['sha256']}
        else:raise ValueError('baseline entry type')
    if not result:raise ValueError('empty baseline inventory')
    return result


def audit(work,inputs=Path('/inputs')):
    work=Path(work)
    before_root=work/'extracted-xacc/tree/install-xacc'
    after_root=work/'install-xacc'
    receipt_path=work/'plugin-normalization.json'
    for root in (work,before_root,after_root,work/'install-core',work/'install-core/lib'):
        if root.is_symlink() or not root.is_dir():raise ValueError('linked or missing audit root')
    if receipt_path.is_symlink() or not receipt_path.is_file():raise ValueError('normalization receipt')
    raw=receipt_path.read_bytes();receipt=json.loads(raw)
    if receipt.get('schema')!='qb.core-plugin-normalization/v1':raise ValueError('normalization schema')
    before=original_entries(inputs)
    if inventory(before_root)!=before:raise ValueError('extracted baseline mutated')
    # Audit originals independently so the generic inventory need not accept
    # cross-prefix links or be weakened for the original installation.
    actual={p.relative_to(after_root).as_posix():p for p in after_root.rglob('*')}
    if not set(before)<=set(actual):raise ValueError('original XACC entry removed')
    for name,entry in before.items():
        path=actual[name]
        import stat
        mode=path.lstat().st_mode
        if entry['type']=='link':
            if not path.is_symlink() or str(path.readlink())!=entry['target']:raise ValueError('original XACC link changed')
        elif entry['type']=='directory':
            if not stat.S_ISDIR(mode) or stat.S_IMODE(mode)!=entry['mode']:raise ValueError('original XACC directory changed')
        elif (not stat.S_ISREG(mode) or stat.S_IMODE(mode)!=entry['mode'] or
              path.stat().st_size!=entry['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']):
            raise ValueError('original XACC file changed')
    changes=receipt.get('changes')
    if not isinstance(changes,list):raise ValueError('normalization changes')
    allowed={}
    for change in changes:
        name=change.get('path','')
        match=re.fullmatch(r'install-xacc/plugins/lib([a-zA-Z0-9_]+)\.so(?:\.[0-9]+)*',name)
        if not match or match.group(1) not in PLUGINS:raise ValueError('unapproved plugin')
        relative=name[len('install-xacc/'):];basename=Path(name).name
        if relative in allowed or relative in before:raise ValueError('duplicate or replaced original plugin')
        target_text='../../install-core/lib/'+basename
        if change.get('before')!='/work/install-core/lib/'+basename or change.get('after')!=target_text:
            raise ValueError('normalization target')
        path=after_root/relative;target=work/'install-core/lib'/basename
        if not path.is_symlink() or str(path.readlink())!=target_text:raise ValueError('plugin link mismatch')
        if not target.is_file() or not target.resolve().is_relative_to((work/'install-core/lib').resolve()):
            raise ValueError('plugin target missing or escaping')
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        if digest!=change.get('target_sha256'):raise ValueError('plugin target hash')
        allowed[relative]=digest
    if set(actual)-set(before)!=set(allowed):raise ValueError('unlisted XACC addition')
    return {'schema':'qb.core-postinstall-audit/v1','passed':True,
            'original_xacc_entries_unchanged':len(before),'added_plugin_links':allowed,
            'normalization_sha256':hashlib.sha256(raw).hexdigest()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work',nargs='?',type=Path,default=Path('/work'))
    parser.add_argument('--inputs',type=Path,default=Path('/inputs'))
    args=parser.parse_args()
    try:result=audit(args.work,args.inputs)
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps({'schema':'qb.core-postinstall-audit/v1','passed':False,'reason':str(error)},sort_keys=True))
        raise SystemExit(1)
    print(json.dumps(result,sort_keys=True))
