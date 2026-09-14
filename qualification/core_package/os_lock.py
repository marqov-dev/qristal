"""Authenticate downloaded Ubuntu packages relative to an explicitly pinned base."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

BASE='ubuntu@sha256:4f838adc7181d9039ac795a7d0aba05a9bd9ecd480d294483169c5def983b64d'
KEY_SHA='1a4dd63e5c76728960a2edddae22e2e0fc53df8e8b87806deb971030ac704eb0'
PREFIX='snapshot.ubuntu.com_ubuntu_20260913T000000Z_dists_'
SUITES=('jammy','jammy-updates','jammy-security')
MAX_INDEX=256*1024*1024


def sha(raw):return hashlib.sha256(raw).hexdigest()


def regular(path,limit):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>limit:raise ValueError('file type/size')
    raw=path.read_bytes()
    if len(raw)>limit:raise ValueError('file grew')
    return raw


def records(text):
    result={};last=None
    for line in text.splitlines()+['']:
        if not line:
            if result:yield result
            result={};last=None;continue
        if line[0].isspace():
            if last is None:raise ValueError('orphan continuation')
            result[last]+='\n'+line[1:];continue
        if ':' not in line:raise ValueError('invalid control field')
        key,value=line.split(':',1)
        if not re.fullmatch('[A-Za-z0-9-]+',key) or key in result:raise ValueError('duplicate/invalid control key')
        result[key]=value.lstrip();last=key


def signed_release(raw,key):
    # Explicit keyring and empty private homedir prevent user trust/config lookup.
    with tempfile.TemporaryDirectory(prefix='qpp-gpgv-') as tmp:
        root=Path(tmp);(root/'key.gpg').write_bytes(key);(root/'InRelease').write_bytes(raw)
        result=subprocess.run(['gpgv','--homedir',str(root),'--keyring',str(root/'key.gpg'),
            '--output',str(root/'Release'),str(root/'InRelease')],
            env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':str(root),'GNUPGHOME':str(root),'LC_ALL':'C'},
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        if result.returncode:raise ValueError('InRelease signature failed')
        return regular(root/'Release',4*1024*1024).decode('utf-8')


def claims(text,suite):
    parsed=list(records(text))
    if len(parsed)!=1 or parsed[0].get('Suite')!=suite or parsed[0].get('Codename')!='jammy':raise ValueError('release suite')
    result={}
    for line in parsed[0].get('SHA256','').splitlines():
        if not line.strip():continue
        fields=line.split()
        if len(fields)!=3 or not re.fullmatch('[a-f0-9]{64}',fields[0]) or not fields[1].isdigit():raise ValueError('release SHA256 entry')
        digest,size,name=fields
        if name in result:raise ValueError('duplicate release path')
        result[name]={'sha256':digest,'bytes':int(size)}
    if not result:raise ValueError('no SHA256 claims')
    return result


def audit(root):
    root=Path(root)
    for name in ('lists','indexes','debs'):
        if (root/name).is_symlink() or not (root/name).is_dir():raise ValueError('input directory')
    key=regular(root/'ubuntu-archive-keyring.gpg',1024*1024)
    if sha(key)!=KEY_SHA:raise ValueError('Ubuntu key identity')
    base=regular(root/'base-status',16*1024*1024)
    if base!=regular(root/'after-status',16*1024*1024):raise ValueError('installed state changed')
    inherited=list(records(base.decode()))
    releases={};release_ids={}
    for suite in SUITES:
        path=root/'lists'/(PREFIX+suite+'_InRelease')
        raw=regular(path,4*1024*1024)
        releases[suite]=claims(signed_release(raw,key),suite)
        release_ids[suite]=sha(raw)
    packages={}
    for path in sorted((root/'debs').iterdir()):
        if not path.name.endswith('.deb'):raise ValueError('unexpected package artifact')
        raw=regular(path,256*1024*1024);digest=sha(raw)
        if digest in packages:raise ValueError('duplicate deb content')
        packages[digest]={'file':path.name,'bytes':len(raw),'sha256':digest,'authenticated_records':[]}
    if not packages or len(packages)>500:raise ValueError('package count')
    seen=set();index_ids={};expanded=0
    for path in sorted((root/'indexes').iterdir()):
        match=re.fullmatch(re.escape(PREFIX)+r'(jammy(?:-updates|-security)?)_(main|universe)_binary-amd64_Packages(?:\.lz4)?\.gz',path.name)
        if not match:raise ValueError('unexpected index name')
        suite,component=match.groups();logical=component+'/binary-amd64/Packages'
        if (suite,component) in seen:raise ValueError('duplicate index')
        seen.add((suite,component))
        regular(path,128*1024*1024)
        with gzip.open(path,'rb') as stream:raw=stream.read(MAX_INDEX+1)
        expanded+=len(raw)
        if len(raw)>MAX_INDEX or expanded>768*1024*1024:raise ValueError('expanded index bound')
        identity={'bytes':len(raw),'sha256':sha(raw)}
        if releases[suite].get(logical)!=identity:raise ValueError('index not bound by signed Release')
        index_ids[suite+'/'+logical]=identity
        for item in records(raw.decode('utf-8')):
            digest=item.get('SHA256')
            if digest not in packages:continue
            package=packages[digest]
            if item.get('Size')!=str(package['bytes']) or item.get('Architecture') not in ('amd64','all'):
                raise ValueError('package signed size/architecture')
            if not re.fullmatch('[a-z0-9][a-z0-9+.-]*',item.get('Package','')) or not item.get('Version') or not item.get('Filename'):
                raise ValueError('package signed identity')
            selected={k:item[k] for k in ('Package','Version','Architecture','Filename')}
            if package['authenticated_records'] and any(package[k]!=selected[k] for k in ('Package','Version','Architecture')):
                raise ValueError('conflicting package identity')
            package.update(selected);package['authenticated_records'].append(suite+'/'+logical)
    if seen!={(s,c) for s in SUITES for c in ('main','universe')}:raise ValueError('missing suite/component index')
    if any(not p['authenticated_records'] for p in packages.values()):raise ValueError('unauthenticated deb')
    return {'schema':'qb.qpp-os-input-lock/v1','base_image':BASE,'snapshot':'20260913T000000Z',
      'keyring_sha256':KEY_SHA,'inrelease_sha256':release_ids,'authenticated_indexes':index_ids,
      'base_status_sha256':sha(base),'base_packages':[{'package':p['Package'],'version':p['Version'],'architecture':p.get('Architecture'),'status':p.get('Status')} for p in inherited],
      'packages':sorted(packages.values(),key=lambda p:p['file']),
      'scope':'authenticated downloads relative to specified base; not standalone closure',
      'resolver_completeness_verified':False,'base_image_origin_verified_by_this_tool':False,
      'installed':False,'runtime_qualified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('inputs',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();result=audit(args.inputs)
    with args.output.open('x') as stream:stream.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'authenticated_packages':len(result['packages']),'installed':False,'runtime_qualified':False}))
