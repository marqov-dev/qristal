"""Bounded tests on an observed Linux x86_64 host and local Docker daemon.

The caller loads and binds the image first. Host observations are not independent
hardware certification. The six-case local probe receipt remains unmodified.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import tempfile
import uuid

HERE=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location('native_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

LOCAL=load('local_probe');WHEEL=load('wheel_linkage_guest');bounded=LOCAL.bounded
MODULES=('qristal.core','numpy','scipy.linalg','symengine','qiskit')
IMPORT_CODE="""import importlib,json
modules=('qristal.core','numpy','scipy.linalg','symengine','qiskit')
items=[]
for name in modules:
 m=importlib.import_module(name)
 items.append({'module':name,'file':getattr(m,'__file__',None),'version':getattr(m,'__version__',None)})
print('QPP_IMPORT_AUDIT '+json.dumps({'schema':'qb.qpp-five-imports/v1','imports':items,'passed':True},sort_keys=True))
"""
CONTEXT_TEMPLATE='{{if eq .Endpoints.docker.Host "unix:///var/run/docker.sock"}}local{{else}}unsupported{{end}}'
INFO_TEMPLATE='{"architecture":{{json .Architecture}},"os":{{json .OSType}}}'
IMAGE_TEMPLATE='{"id":{{json .Id}},"architecture":{{json .Architecture}},"os":{{json .Os}}}'


def require(ok,message):
    if not ok:raise ValueError(message)


def pairs(items):
    out={}
    for k,v in items:
        require(k not in out,'duplicate JSON key');out[k]=v
    return out


def parse(raw):
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def capture(command,timeout=30):
    code,out,err=bounded.capture(command,timeout=timeout,stdout_limit=131072,stderr_limit=65536)
    return {'command':command,'exit_code':code,'stdout':out.decode(),'stderr':err.decode()}


def observe(image,records=None):
    require(platform.system()=='Linux' and platform.machine()=='x86_64','Linux x86_64 host required')
    # Do not echo endpoint/env values: remote URLs can contain credentials.
    require(os.environ.get('DOCKER_HOST','') in ('','unix:///var/run/docker.sock'),'local Docker socket required')
    require(os.environ.get('DOCKER_CONTEXT','') in ('','default'),'default Docker context required')
    require(not os.environ.get('DOCKER_TLS_VERIFY') and not os.environ.get('DOCKER_CERT_PATH'),'Docker TLS overrides forbidden')
    records=[] if records is None else records
    record=capture(['uname','-s','-m']);records.append(record)
    require(record['exit_code']==0 and not record['stderr'] and record['stdout'].strip()=='Linux x86_64','uname mismatch')
    record=capture(['docker','context','inspect','--format',CONTEXT_TEMPLATE]);records.append(record)
    require(record['exit_code']==0 and not record['stderr'] and record['stdout'].strip()=='local','nonlocal Docker context')
    record=capture(['docker','info','--format',INFO_TEMPLATE]);records.append(record)
    require(record['exit_code']==0 and not record['stderr'],'Docker info failed')
    info=parse(record['stdout']);require(info['architecture'] in ('x86_64','amd64') and info['os']=='linux','Docker platform mismatch')
    record=capture(['docker','image','inspect','--format',IMAGE_TEMPLATE,image]);records.append(record)
    require(record['exit_code']==0 and not record['stderr'],'loaded image missing')
    inspected=parse(record['stdout']);require(inspected=={'id':image,'architecture':'amd64','os':'linux'},'loaded image identity/platform mismatch')
    return {'kernel_system':platform.system(),'kernel_machine':platform.machine(),
            'daemon_architecture':info['architecture'],'daemon_os':info['os'],
            'local_socket_observed':True,'commands':records}


def confinement(name,image):
    return ['docker','run','--rm','--name',name,'--platform','linux/amd64','--network','none',
            '--read-only','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256',
            '--cap-drop','ALL','--security-opt','no-new-privileges','--user','65532:65532',
            '--tmpfs','/tmp:rw,exec,size=512m']


def audit_valid(label,text):
    marker='QPP_IMPORT_AUDIT ' if label=='imports' else 'QPP_WHEEL_AUDIT '
    require(text.startswith(marker) and text.count('\n')==1 and text.endswith('\n'),'audit marker/line')
    data=parse(text[len(marker):]);require(data.get('passed') is True,'audit not passed')
    if label=='imports':
        require(data.get('schema')=='qb.qpp-five-imports/v1','imports schema')
        imports=data.get('imports');require(isinstance(imports,list) and [i.get('module') for i in imports]==list(MODULES),'five imports required')
        require(all(isinstance(i.get('file'),str) and i['file'].startswith('/work/') for i in imports),'installed imports required')
    else:
        require(data.get('schema')=='qb.qpp-installed-wheel-linkage/v1' and data.get('mode')==label,'wheel schema/mode')
        require(data.get('loader_overrides') is False and data.get('svd_reconstruction_passed') is True,'wheel claims')
        require(data.get('matrix_product')==[[10.,5.],[5.,5.]] and data.get('solution')==[2.,3.],'wheel arithmetic')
        libs=data.get('mapped_libraries');require(isinstance(libs,list) and 0<len(libs)<=64,'mapped libraries')
        paths=[]
        for item in libs:
            name=item.get('path');require(isinstance(name,str) and name.startswith('/work/python-core/') and '..' not in Path(name).parts,'mapped path')
            require(type(item.get('bytes')) is int and 0<item['bytes']<=512*1024**2 and isinstance(item.get('sha256'),str) and re.fullmatch('[a-f0-9]{64}',item['sha256']),'mapped identity')
            paths.append(name)
        require(len(set(paths))==len(paths) and WHEEL.mappings_cover(label,paths),'mapped library coverage')
    return data


def case(label,image,script):
    name='qpp-native-'+uuid.uuid4().hex[:16]
    command=confinement(name,image)
    if label!='imports':command+=['--mount','type=bind,source='+str(script)+',target=/audit.py,readonly']
    command+=['--entrypoint','/work/python-core/bin/python',image]
    command+=['-c',IMPORT_CODE] if label=='imports' else ['/audit.py',label]
    result={'case':label,'command':command,'passed':False}
    try:
        result.update(capture(command,timeout=90))
        require(result['exit_code']==0 and result['stderr']=='','audit command failed')
        result['audit']=audit_valid(label,result['stdout']);result['passed']=True
    except Exception as error:result['error']=type(error).__name__
    finally:
        cleanup={'absence_verified':False,'commands':[]}
        try:
            cleanup['commands'].append(capture(['docker','rm','-f',name],timeout=15))
        except Exception as error:cleanup['remove_error']=type(error).__name__
        try:
            inspected=capture(['docker','container','inspect','--format','{{.Id}}',name],timeout=15)
            cleanup['commands'].append(inspected)
            cleanup['absence_verified']=LOCAL.absence(inspected['exit_code'],inspected['stdout'].encode(),inspected['stderr'].encode(),name)
        except Exception as error:cleanup['error']=type(error).__name__
        result['cleanup']=cleanup;result['passed']=result['passed'] and cleanup['absence_verified']
    return result


def local_valid(receipt,image):
    require(receipt.get('schema')=='qb.qpp-local-emulation-probe/v1' and receipt.get('image_id')==image and receipt.get('passed') is True,'local receipt schema/identity')
    require(all(receipt.get(k) is False for k in ('native_amd64_hardware','hosted','redistribution_cleared')),'raw local scope changed')
    cases=receipt.get('cases');require(isinstance(cases,list) and [x.get('case') for x in cases]==['capabilities','identity','bell','q0','reject-aer','reject-noise'],'local case set')
    for item in cases:
        require(item.get('passed') is True and item.get('cleanup',{}).get('absence_verified') is True,'local case/cleanup failed')
        command=item.get('command',[]);require('--name' in command and command[command.index('--name')+2]==image,'local command identity')


def run(image,output):
    require(isinstance(image,str) and re.fullmatch('sha256:[a-f0-9]{64}',image),'immutable image digest required')
    output=Path(output);local_output=output.with_name(output.stem+'.local-probe.json')
    require(not output.exists() and not local_output.exists(),'new output required')
    result={'schema':'qb.qpp-native-host-probe/v1','image_id':image,'passed':False,
            'native_host_observed':False,'hardware_certified':False,'hosted':False,'redistribution_cleared':False,'cases':[]}
    try:
        result['host_commands']=[]
        result['host']=observe(image,result['host_commands']);result['native_host_observed']=True
        receipt=LOCAL.probe(image,local_output)
        with local_output.open('rb') as stream:raw=stream.read(1024**2+1)
        require(len(raw)<=1024**2 and parse(raw)==receipt,'local raw receipt mismatch')
        result['local_probe']=receipt
        result['local_receipt']={'filename':local_output.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        local_valid(receipt,image)
        with tempfile.TemporaryDirectory(prefix='qpp-native-audit-') as tmp:
            path=Path(tmp);path.chmod(0o755);script=path/'wheel_linkage_guest.py'
            with (HERE/'wheel_linkage_guest.py').open('rb') as stream:raw=stream.read(65537)
            require(len(raw)<=65536,'wheel script size')
            script.write_bytes(raw);script.chmod(0o644)
            result['wheel_probe_source_sha256']=hashlib.sha256(raw).hexdigest()
            result['imports_source_sha256']=hashlib.sha256(IMPORT_CODE.encode()).hexdigest()
            result['cases']=[case(label,image,script) for label in ('imports','numpy','scipy')]
        result['passed']=all(c['passed'] for c in result['cases'])
    except Exception as error:result['error']=type(error).__name__
    with output.open('x') as f:f.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image');p.add_argument('output',type=Path)
    result=run(**vars(p.parse_args()));print(json.dumps({'passed':result['passed'],'native_host_observed':result['native_host_observed']}))
    if not result['passed']:raise SystemExit(1)
