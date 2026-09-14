"""Inventory bundled license evidence; no extraction or legal/compliance conclusion."""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import zipfile

MAX_ARCHIVE=1024**3
MAX_MEMBERS=100000
MAX_MEMBER=4*1024**2
MAX_NOTICE_TOTAL=32*1024**2


def sha(data):return hashlib.sha256(data).hexdigest()


def file_sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while data:=stream.read(1024**2):digest.update(data)
    return digest.hexdigest()


def safe_name(name):
    path=PurePosixPath(name.rstrip('/'))
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or str(path)!=name.rstrip('/'):
        raise ValueError('unsafe archive name')
    return str(path)


def is_notice(name):
    return bool(re.match(r'^(licen[cs]e|copying|copyright|notice|authors)([._-].*|$)',PurePosixPath(name).name,re.I))


def bound_read(stream,size):
    if not 0<=size<=MAX_MEMBER:raise ValueError('notice member bound')
    raw=stream.read(MAX_MEMBER+1)
    if len(raw)!=size:raise ValueError('notice read size')
    return raw


def evidence(name,raw):
    return {'path':name,'bytes':len(raw),'sha256':sha(raw)}


def scan_wheel(path):
    notices=[];metadata=[];seen=set();expanded=0;notice_bytes=0
    with zipfile.ZipFile(path) as archive:
        members=archive.infolist()
        if len(members)>MAX_MEMBERS:raise ValueError('wheel member bound')
        for member in members:
            name=safe_name(member.filename)
            if name in seen:raise ValueError('duplicate wheel member')
            seen.add(name)
            mode=member.external_attr>>16
            if stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR):raise ValueError('wheel special member')
            expanded+=member.file_size
            if member.file_size<0 or expanded>MAX_ARCHIVE:raise ValueError('wheel expanded bound')
            if member.is_dir():continue
            is_metadata=name.endswith('.dist-info/METADATA') and len(PurePosixPath(name).parts)==2
            if not is_metadata and not is_notice(name):continue
            notice_bytes+=member.file_size
            if notice_bytes>MAX_NOTICE_TOTAL:raise ValueError('wheel notice byte bound')
            with archive.open(member) as stream:raw=bound_read(stream,member.file_size)
            if is_metadata:metadata.append((name,raw))
            else:notices.append(evidence(name,raw))
    if len(metadata)!=1:raise ValueError('unique wheel METADATA required')
    name,raw=metadata[0];message=BytesParser().parsebytes(raw,headersonly=True)
    fields={}
    for field in ('Name','Version','License','License-Expression','License-File','Classifier'):
        values=message.get_all(field,[])
        if field=='Classifier':values=[v for v in values if v.startswith('License ::')]
        fields[field]=[str(value)[:8192] for value in values]
    declared=fields['License-File'];dist_info=str(PurePosixPath(name).parent)
    missing=[]
    with zipfile.ZipFile(path) as archive:
        members={safe_name(item.filename):item for item in archive.infolist()}
        for item in declared:
            safe_name(item)
            candidates=[dist_info+'/'+item,dist_info+'/licenses/'+item]
            found=next((candidate for candidate in candidates if candidate in members and not members[candidate].is_dir()),None)
            if found is None:missing.append(item);continue
            if any(n['path']==found for n in notices):continue
            member=members[found];notice_bytes+=member.file_size
            if notice_bytes>MAX_NOTICE_TOTAL:raise ValueError('wheel notice byte bound')
            with archive.open(member) as stream:raw_notice=bound_read(stream,member.file_size)
            notices.append(evidence(found,raw_notice))
    return {'filename':path.name,'metadata':dict(evidence(name,raw),fields=fields),
            'notice_files':notices,'declared_license_files_not_found':missing,
            'coverage':'bundled notice files observed' if notices else 'no filename-matched notice files observed'}


def scan_work(path):
    notices=[];seen=set();total=0;notice_bytes=0
    with tarfile.open(path,'r|') as archive:
        for member in archive:
            name=safe_name(member.name)
            if name in seen or len(seen)>=MAX_MEMBERS:raise ValueError('tar member bound/duplicate')
            seen.add(name);total+=member.size
            if member.size<0 or total>MAX_ARCHIVE:raise ValueError('tar expanded bound')
            if not(member.isfile() or member.isdir() or member.issym()):raise ValueError('tar special member')
            if member.isfile() and is_notice(name):
                notice_bytes+=member.size
                if notice_bytes>MAX_NOTICE_TOTAL:raise ValueError('native notice byte bound')
                with archive.extractfile(member) as stream:raw=bound_read(stream,member.size)
                notices.append(evidence(name,raw))
    return {'notice_files':notices,'install_roots_without_filename_matched_notices':[
        root for root in ('install-core','install-xacc') if not any(n['path'].startswith(root+'/') for n in notices)],
        'coverage':'filename scan only; embedded source notices and transitive component coverage not established'}


def scan(context):
    context=Path(context)
    if context.is_symlink():raise ValueError('symlink context')
    context=context.resolve();manifest=context/'staging.json'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>32*1024**2:raise ValueError('staging manifest')
    raw=manifest.read_bytes();staging=json.loads(raw)
    if staging.get('schema')!='qb.core-staged-inputs/v1' or staging.get('staged') is not True:raise ValueError('staged inputs required')
    inventory=staging['inventory']
    names=sorted(name for name in inventory if name.startswith('python/wheels/') and name.endswith('.whl'))
    if len(names)!=51:raise ValueError('expected staged wheel count')
    if {p.name for p in (context/'python/wheels').iterdir()}!={PurePosixPath(n).name for n in names}:raise ValueError('wheel directory mismatch')
    bindings={}
    def checked(name,scanner):
        safe_name(name);path=context/name;entry=inventory[name]
        if any(parent.is_symlink() for parent in (path,*path.parents) if parent==context or context in parent.parents):raise ValueError('symlink input')
        if entry.get('type')!='file' or not path.is_file() or path.stat().st_size!=entry['bytes'] or entry['bytes']>MAX_ARCHIVE:raise ValueError('staged file type/size')
        if file_sha(path)!=entry['sha256']:raise ValueError('staged file identity')
        result=scanner(path)
        if file_sha(path)!=entry['sha256']:raise ValueError('staged file changed')
        bindings[name]={'bytes':entry['bytes'],'sha256':entry['sha256']}
        return result
    wheels=[checked(name,scan_wheel) for name in names]
    work=checked('work.tar',scan_work)
    if manifest.read_bytes()!=raw:raise ValueError('staging manifest changed')
    return {'schema':'qb.core-notice-inventory/v1','staging_sha256':sha(raw),'scanner_sha256':file_sha(Path(__file__)),
            'input_bindings':bindings,'wheel_count':len(wheels),'wheels':wheels,'native':work,
            'wheel_notice_file_count':sum(len(w['notice_files']) for w in wheels),
            'wheels_without_filename_matched_notices':[w['filename'] for w in wheels if not w['notice_files']],
            'coverage_complete':False,'legal_conclusion':None,
            'remaining_coverage':['exact native source and dependency notices, including embedded headers',
                                  'final OS package notices and dependencies','review redistribution requirements and attribution text'],
            'limitations':['Inventory records available metadata and named files, not license grants or compliance.',
                           'Staging hashes bind supplied bytes; this scan does not rerun native qualification.',
                           'Filename matching does not find all embedded notices or identify every native component.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('context',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=scan(args.context)
    with args.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:result[k] for k in ('wheel_count','wheel_notice_file_count','coverage_complete')}))

if __name__=='__main__':main()
