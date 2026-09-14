"""Assemble pinned attribution evidence; never claim complete license coverage."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tarfile
import tempfile
import zipfile

HERE=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location('attribution_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

STAGE=load('stage');NOTICES=load('notices')
STAGING_SHA='99cf64873510ba102b6c83cebf186023a7f0de06e81191f29e038939321be863'
SOURCE_SHA='74659b67ff455a97a156edad96b1360d68f9dcac6420d2c3afca0321762d4f62'
UPSTREAM_SHA='7a92eb96872ced81db4603b663ecbe9b1a8601ff9e2bdc66bc9bd82ca4caec9b'


def path_at(root,name):
    if NOTICES.safe_name(name)!=name:raise ValueError('noncanonical path')
    path=root/name
    if root.is_symlink() or any(p.is_symlink() for p in (path,*path.parents) if p==root or root in p.parents):raise ValueError('symlink input path')
    return path



def exact_files(root,entries,manifest_name):
    expected={name for name,entry in entries.items() if entry.get('type')!='directory'}|{manifest_name}
    for name in expected:path_at(root,name)
    actual=set();pending=[root];count=0
    while pending:
        directory=pending.pop()
        with os.scandir(directory) as stream:
            for entry in stream:
                count+=1
                if count>100000:raise ValueError('input inventory member bound')
                if entry.is_symlink():raise ValueError('input inventory symlink')
                if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):actual.add(Path(entry.path).relative_to(root).as_posix())
                else:raise ValueError('input inventory special file')
    if actual!=expected:raise ValueError('input file inventory mismatch')


def pin(root,name,destination,expected):
    source=path_at(root,name);destination.parent.mkdir(parents=True,exist_ok=True)
    return STAGE.snapshot(source,destination,expected['bytes'],{'bytes':expected['bytes'],'sha256':expected['sha256']})


def pinned_document(root,name,destination,digest):
    source=path_at(root,name)
    identity=STAGE.snapshot(source,destination,32*1024**2)
    if identity['sha256']!=digest:raise ValueError('pinned inventory identity')
    return STAGE.AUDIT.parse(destination.read_bytes())


def write_notice(root,name,raw,expected,category,origin,entries):
    NOTICES.safe_name(name)
    if name in entries or len(raw)!=expected['bytes'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:raise ValueError('notice identity/duplicate')
    target=path_at(root,name);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    target.chmod(0o644)
    entries[name]={'bytes':len(raw),'sha256':expected['sha256'],'category':category,'origin':origin}


def build(context,source_bundle,upstream_bundle,output):
    context,source_bundle,upstream_bundle,output=map(Path,(context,source_bundle,upstream_bundle,output))
    if output.exists() or output.is_symlink():raise FileExistsError('new output required')
    with tempfile.TemporaryDirectory(prefix='.attribution-',dir=output.parent) as temporary:
        private=Path(temporary);snapshot=private/'context';snapshot.mkdir()
        staging=pinned_document(context,'staging.json',snapshot/'staging.json',STAGING_SHA)
        inventory=staging['inventory']
        exact_files(context,inventory,'staging.json')
        selected=[name for name in inventory if name=='work.tar' or name.startswith('python/wheels/')]
        for name in selected:
            if inventory[name]['type']=='directory':continue
            pin(context,name,snapshot/name,inventory[name])
        observed=NOTICES.scan(snapshot)
        source_inventory=pinned_document(source_bundle,'inventory.json',private/'source-inventory.json',SOURCE_SHA)
        upstream_inventory=pinned_document(upstream_bundle,'inventory.json',private/'upstream-inventory.json',UPSTREAM_SHA)
        exact_files(source_bundle,source_inventory['entries'],'inventory.json')
        exact_files(upstream_bundle,upstream_inventory['files'],'inventory.json')
        payload=private/'payload';payload.mkdir();entries={}
        for wheel in observed['wheels']:
            archive_path=snapshot/'python/wheels'/wheel['filename']
            with zipfile.ZipFile(archive_path) as archive:
                for item in wheel['notice_files']:
                    with archive.open(item['path']) as stream:raw=NOTICES.bound_read(stream,item['bytes'])
                    write_notice(payload,'wheel/'+wheel['filename']+'/'+item['path'],raw,item,'bundled-wheel',
                                 {'wheel':wheel['filename'],'member':item['path']},entries)
        wanted={item['path']:item for item in observed['native']['notice_files']}
        with tarfile.open(snapshot/'work.tar','r|') as archive:
            for member in archive:
                if member.name in wanted:
                    item=wanted[member.name]
                    if not member.isfile():raise ValueError('native notice type')
                    with archive.extractfile(member) as stream:raw=NOTICES.bound_read(stream,item['bytes'])
                    write_notice(payload,'native/'+member.name,raw,item,'bundled-native',{'member':member.name},entries)
        if sum(e['category']=='bundled-native' for e in entries.values())!=len(wanted):raise ValueError('missing native notice')
        source_names=[name for name in source_inventory['entries'] if name.startswith(('materials/','xacc-source/'))]
        if len(source_names)!=35:raise ValueError('source notice count')
        for category,bundle,items in [('verified-source',source_bundle,{n:source_inventory['entries'][n] for n in source_names}),
                ('upstream-release-candidate',upstream_bundle,{n:upstream_inventory['files'][n] for n in ('antlr/LICENSE.txt','openpulse/LICENSE')})]:
            for name,item in items.items():
                copied=private/'supplemental'/category/name
                pin(bundle,name,copied,item)
                raw=copied.read_bytes()
                write_notice(payload,category+'/'+name,raw,item,category,{'inventory_path':name},entries)
        index={'schema':'qb.attribution-payload/v1','coverage_complete':False,'legal_conclusion':None,
               'bindings':{'staging_sha256':STAGING_SHA,'source_inventory_sha256':SOURCE_SHA,'upstream_inventory_sha256':UPSTREAM_SHA,
                           'assembler_sha256':NOTICES.file_sha(Path(__file__)),'scanner_sha256':NOTICES.file_sha(HERE/'notices.py')},
               'notice_count':len(entries),'entries':entries,'observations':observed,
               'limitations':['Upstream release candidates are not proof of inclusion in acquired wheels.',
                              'Source notices are separately recovered evidence, not proof they were installed.',
                              'OS documentation remains in the final image; it is not copied or reviewed by this payload.',
                              'Embedded notices and full distributed dependency coverage require further reconciliation.']}
        (payload/'README.txt').write_text('Attribution evidence collection\n\nBundled wheel/native notices, verified source notices, and upstream release candidates are separated by directory and indexed by SHA-256.\nThis is an incomplete evidence collection, not legal clearance or a declaration that redistribution requirements are satisfied.\nOS documentation remains in the final image. See ATTRIBUTION_INDEX.json for provenance and remaining coverage limitations.\n')
        index['files']={name:{'bytes':entry['bytes'],'sha256':entry['sha256']} for name,entry in entries.items()}
        readme=payload/'README.txt'
        index['files']['README.txt']={'bytes':readme.stat().st_size,'sha256':NOTICES.file_sha(readme)}
        (payload/'ATTRIBUTION_INDEX.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
        for path in payload.rglob('*'):path.chmod(0o755 if path.is_dir() else 0o644)
        payload.chmod(0o755)
        output.mkdir(mode=0o700)
        try:os.replace(payload,output)
        except Exception:output.rmdir();raise
        return index


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('context','source_bundle','upstream_bundle','output'):parser.add_argument(name,type=Path)
    result=build(**vars(parser.parse_args()))
    print(json.dumps({'notice_count':result['notice_count'],'coverage_complete':False}))

if __name__=='__main__':main()
