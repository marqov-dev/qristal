"""Bounded raw native-image receipts; no cloud binding or execution side effects."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_BYTES=2*1024**2
FILES={'execution.json','probes.json','probes.local-probe.json'}
IMAGE='sha256:03a2db140fdb579f3d6376700c36016af2bd3ffa139aeb5282439498a9a4aa2f'
CONFIG='sha256:0127d58acfa19aae8fe4ab911b1acbb9993d8ab16ebd40ad55421480457907f0'
ARCHIVE_SHA='451b0710cea596fcae3bf717caed723ab18677cab0e3354b11c3db9761a96ab5'
ARCHIVE_BYTES=514349056
MODULES=['qristal.core','numpy','scipy.linalg','symengine','qiskit']


def require(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'duplicate JSON key');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def read(path):
    path=Path(path)
    require(not any(p.is_symlink() for p in (path,*path.parents)),'symlink input')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode) and before.st_size<=MAX_BYTES,'regular bounded evidence required')
        raw=stream.read(MAX_BYTES+1);after=os.fstat(stream.fileno())
    require(len(raw)<=MAX_BYTES and len(raw)==before.st_size,'evidence byte bound')
    require((before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_size,after.st_mtime_ns,after.st_ctime_ns),'evidence changed')
    return raw


def record(raw):return {'text':raw.decode('utf-8'),'bytes':len(raw),'sha256':sha(raw)}


def unpack(item):
    require(isinstance(item,dict) and set(item)=={'text','bytes','sha256'},'raw record fields')
    require(isinstance(item['text'],str) and type(item['bytes']) is int,'raw record types')
    raw=item['text'].encode('utf-8')
    require(len(raw)<=MAX_BYTES and len(raw)==item['bytes'] and sha(raw)==item['sha256'],'raw record identity')
    return raw


def pack(directory,protocol_path,output):
    directory,output=Path(directory),Path(output)
    require(not directory.is_symlink() and directory.is_dir(),'result directory')
    names={p.name for p in directory.iterdir()}
    require('execution.json' in names and names<=FILES,'result file set')
    files={name:record(read(directory/name)) for name in sorted(names)}
    envelope={'schema':'qb.native-image-evidence/v1','protocol':record(read(protocol_path)),'files':files}
    raw=(json.dumps(envelope,sort_keys=True,separators=(',',':'))+'\n').encode()
    require(len(raw)<=MAX_BYTES,'envelope byte bound')
    require(not any(p.is_symlink() for p in output.parents),'symlink output parent')
    fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    return {'bytes':len(raw),'sha256':sha(raw)}


def audit_valid(label,text):
    marker='QPP_IMPORT_AUDIT ' if label=='imports' else 'QPP_WHEEL_AUDIT '
    require(isinstance(text,str) and text.startswith(marker) and text.count('\n')==1 and text.endswith('\n'),'audit marker')
    data=parse(text[len(marker):]);require(data.get('passed') is True,'audit failed')
    if label=='imports':
        require(data.get('schema')=='qb.qpp-five-imports/v1','import schema')
        items=data.get('imports');require(isinstance(items,list) and [i.get('module') for i in items]==MODULES,'five imports')
        require(all(isinstance(i.get('file'),str) and i['file'].startswith('/work/') and '..' not in Path(i['file']).parts for i in items),'installed imports')
    else:
        require(data.get('schema')=='qb.qpp-installed-wheel-linkage/v1' and data.get('mode')==label,'wheel schema')
        require(data.get('loader_overrides') is False and data.get('svd_reconstruction_passed') is True,'wheel claims')
        require(data.get('matrix_product')==[[10.,5.],[5.,5.]] and data.get('solution')==[2.,3.],'wheel arithmetic')
        libraries=data.get('mapped_libraries');require(isinstance(libraries,list) and 0<len(libraries)<=64,'mapped libraries')
        paths=[]
        for item in libraries:
            path=item.get('path');require(isinstance(path,str) and path.startswith('/work/python-core/') and '..' not in Path(path).parts,'mapped path')
            require(type(item.get('bytes')) is int and 0<item['bytes']<=512*1024**2 and isinstance(item.get('sha256'),str) and re.fullmatch('[a-f0-9]{64}',item['sha256']),'mapped identity')
            paths.append(path)
        require(len(paths)==len(set(paths)),'duplicate mapped libraries')
        for root in (('numpy','scipy') if label=='scipy' else ('numpy',)):
            for token in ('openblas','libgfortran','libquadmath'):
                require(any('/'+root+'.libs/' in path and token in Path(path).name for path in paths),'mapped library coverage')
    return data


def classify(execution,protocol,files):
    require(execution.get('schema')=='qb.native-image-execution/v1' and type(execution.get('passed')) is bool,'execution schema')
    result={'native_passed':False,'cloud_instance_binding_verified':False,'resource_cleanup_verified':False,'hosted':False,'redistribution_cleared':False}
    if execution['passed'] is False:return result
    require(set(files)==FILES,'successful result file set')
    require(not execution.get('error'),'successful execution error')
    require(all(execution.get(k) is False for k in ('cloud_instance_binding_verified','resource_cleanup_verified','hosted','redistribution_cleared')),'unsupported execution scope')
    proof=execution.get('archive_verification',{})
    for key,value in {'image_index_digest':IMAGE,'config_digest':CONFIG,'archive_sha256':ARCHIVE_SHA,'archive_bytes':ARCHIVE_BYTES,'layer_diff_ids_verified':True}.items():
        require(proof.get(key)==value and type(proof.get(key)) is type(value),'archive proof '+key)
    selected=execution.get('execution_digest');require(selected in (IMAGE,CONFIG),'execution image identity')
    require(execution.get('host_architecture') in ('x86_64','amd64') and execution.get('engine_platform') in ('linux x86_64','linux amd64') and execution.get('empty_daemon_observed_before_load') is True,'execution host')
    probe=parse(files['probes.json']);local=parse(files['probes.local-probe.json'])
    require(execution.get('probe')==probe,'execution/probe binding')
    require(probe.get('schema')=='qb.qpp-native-host-probe/v1' and probe.get('image_id')==selected and probe.get('passed') is True and probe.get('native_host_observed') is True,'native probe')
    require(all(probe.get(k) is False for k in ('hardware_certified','hosted','redistribution_cleared')),'probe scope')
    host=probe.get('host',{})
    require(host.get('kernel_system')=='Linux' and host.get('kernel_machine')=='x86_64' and host.get('daemon_architecture') in ('amd64','x86_64') and host.get('daemon_os')=='linux' and host.get('local_socket_observed') is True,'probe host')
    require(probe.get('local_probe')==local,'local probe binding')
    require(probe.get('local_receipt')=={'filename':'probes.local-probe.json','bytes':len(files['probes.local-probe.json']),'sha256':sha(files['probes.local-probe.json'])},'local raw receipt binding')
    require(local.get('schema')=='qb.qpp-local-emulation-probe/v1' and local.get('image_id')==selected and local.get('passed') is True,'local receipt')
    require(all(local.get(k) is False for k in ('native_amd64_hardware','hosted','redistribution_cleared')),'local scope')
    cases=local.get('cases');require(isinstance(cases,list) and [c.get('case') for c in cases]==['capabilities','identity','bell','q0','reject-aer','reject-noise'],'six local cases')
    for case in cases:
        require(case.get('passed') is True and case.get('cleanup',{}).get('absence_verified') is True,'local case cleanup')
        command=case.get('command',[])
        require('--name' in command and len(command)>command.index('--name')+2 and command[command.index('--name')+2]==selected,'local command image')
    cases=probe.get('cases');require(isinstance(cases,list) and [c.get('case') for c in cases]==['imports','numpy','scipy'],'three audit cases')
    for case in cases:
        require(case.get('passed') is True and case.get('exit_code')==0 and case.get('stderr')=='' and case.get('cleanup',{}).get('absence_verified') is True,'audit case cleanup')
        require(audit_valid(case['case'],case.get('stdout'))==case.get('audit'),'parsed audit binding')
        require(selected in case.get('command',[]),'audit command image')
    result['native_passed']=True
    return result


def verify(path,expected,protocol_sha256):
    raw=read(path)
    require(expected=={'bytes':len(raw),'sha256':sha(raw)},'external envelope identity')
    envelope=parse(raw);require(isinstance(envelope,dict) and set(envelope)=={'schema','protocol','files'} and envelope['schema']=='qb.native-image-evidence/v1','envelope schema')
    protocol_raw=unpack(envelope['protocol']);require(sha(protocol_raw)==protocol_sha256,'external protocol identity')
    protocol=parse(protocol_raw)
    require(protocol.get('schema')=='qb.native-image-protocol/v1' and protocol.get('image_index_digest')==IMAGE and protocol.get('config_digest')==CONFIG,'pinned protocol')
    require(protocol.get('files',{}).get('image.tar')=={'bytes':ARCHIVE_BYTES,'sha256':ARCHIVE_SHA},'protocol archive')
    records=envelope['files'];require(isinstance(records,dict) and 'execution.json' in records and set(records)<=FILES,'evidence file set')
    files={name:unpack(item) for name,item in records.items()}
    parsed={name:parse(raw) for name,raw in files.items()}
    schemas={'execution.json':'qb.native-image-execution/v1','probes.json':'qb.qpp-native-host-probe/v1',
             'probes.local-probe.json':'qb.qpp-local-emulation-probe/v1'}
    require(all(isinstance(item,dict) and item.get('schema')==schemas[name] for name,item in parsed.items()),'retained receipt schema')
    execution=parsed['execution.json']
    require(execution.get('protocol_sha256')==protocol_sha256,'execution protocol identity')
    classification=classify(execution,protocol,files)
    return {'verified':True,'execution':execution,'protocol':protocol,'classification':classification,
            'files':files,'envelope_sha256':sha(raw)}


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('pack');p.add_argument('directory');p.add_argument('protocol_path');p.add_argument('output')
    args=vars(parser.parse_args());args.pop('command');print(json.dumps(pack(**args)))

if __name__=='__main__':main()
