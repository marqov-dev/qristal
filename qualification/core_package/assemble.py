"""Create a private offline Docker context from staged QPP and authenticated OS inputs."""
import argparse
import importlib.util
import json
import hashlib
from pathlib import Path
import os
import tempfile

HERE=Path(__file__).resolve().parent

def load(name):
    spec=importlib.util.spec_from_file_location('qpp_assembly_'+name,HERE/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

STAGE=load('stage')
OS=load('os_lock')

def assemble(staged,os_inputs,output,expected_staging_sha256):
    staged,os_inputs,output=map(Path,(staged,os_inputs,output))
    if output.exists() or output.is_symlink():raise FileExistsError('new output required')
    lock=OS.audit(os_inputs)
    receipt=OS.regular(staged/'staging.json',8*1024**2)
    receipt_sha=hashlib.sha256(receipt).hexdigest()
    if receipt_sha!=expected_staging_sha256:raise ValueError('staging receipt identity')
    raw=STAGE.AUDIT.parse(receipt)
    if raw.get('schema')!='qb.core-staged-inputs/v1' or raw.get('staged') is not True:
        raise ValueError('staged evidence required')
    with tempfile.TemporaryDirectory(prefix='.qpp-assembly-',dir=output.parent) as d:
        work=Path(d)/'context';work.mkdir()
        selected={n:e for n,e in raw['inventory'].items() if n=='work.tar' or n.startswith(('runtime/','python/wheels/'))}
        for name,item in selected.items():
            STAGE.AUDIT.OUTPUT.safe_name(name)
            if item['type']=='directory':continue
            if item['type']!='file':raise ValueError('context input must be regular')
            target=work/name;target.parent.mkdir(parents=True,exist_ok=True)
            STAGE.snapshot(staged/name,target,item['bytes'],{'bytes':item['bytes'],'sha256':item['sha256']})
            target.chmod(0o644)
        required=['work.tar','runtime/qpp_runtime.py','runtime/requirements.txt','runtime/install-python.sh']
        if any(n not in selected for n in required):raise ValueError('missing runtime input')
        (work/'os/debs').mkdir(parents=True)
        for item in lock['packages']:
            name=item['file']
            if Path(name).name!=name or not name.endswith('.deb'):raise ValueError('deb filename')
            STAGE.snapshot(os_inputs/'debs'/name,work/'os/debs'/name,item['bytes'],{'bytes':item['bytes'],'sha256':item['sha256']})
            (work/'os/debs'/name).chmod(0o644)
        (work/'Dockerfile').write_bytes((HERE/'os/Dockerfile').read_bytes())
        (work/'.dockerignore').write_text('assembly.json\n')
        result={'schema':'qb.qpp-offline-build-inputs/v1','os_lock':lock,
                'staging_sha256':receipt_sha,
                'evidence_provenance':raw['evidence_provenance'],
                'inventory':STAGE.context_inventory(work),'assembled':True,
                'built':False,'runtime_qualified':False,'redistribution_cleared':False}
        (work/'assembly.json').write_text(json.dumps(result,indent=2)+'\n')
        output.mkdir()
        try:os.replace(work,output)
        except Exception:
            output.rmdir();raise
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('staged','os_inputs','output'):p.add_argument(name,type=Path)
    p.add_argument('--expected-staging-sha256',required=True)
    result=assemble(**vars(p.parse_args()))
    print(json.dumps({k:result[k] for k in ('assembled','built','runtime_qualified','redistribution_cleared')}))
