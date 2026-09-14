"""Freeze and archive the exact public inputs for one bounded Core CPU run."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile

HERE=Path(__file__).resolve().parent
BASE='ubuntu@sha256:4f838adc7181d9039ac795a7d0aba05a9bd9ecd480d294483169c5def983b64d'
TOOLCHAIN_SHA='84c984b8dae5801ed276d5db90ab0a1f6426802ba043d5d2d7a18c1f5186cce1'
OPERATOR_FILES=('core_native/run.py','core_native/report_reference.py','core_native/check_result.py','core_output/output.py',
 'source_artifact/run.py','source_artifact/archive.py','source_build/run.py',
 'full_decoder/cloud/run.py','gpu_release/supervisor.py','gpu_release/observer.py',
 'gpu_package/console.py','source_artifact/requirements-operator.txt')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while data:=stream.read(1024*1024):digest.update(data)
    return digest.hexdigest()


def package(core,dependencies,xacc,python,toolchain,output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('new output required')
    if sha(toolchain)!=TOOLCHAIN_SHA:raise ValueError('toolchain identity')
    output.mkdir(parents=True);work=output/'work';work.mkdir()
    inputs=work/'inputs'
    prepare=load('core_material_preparation',HERE/'prepare.py')
    prepare.prepare(core,dependencies,xacc,python,inputs)
    extras={
       'native/report_reference.py':HERE/'report_reference.py',
       'output/output.py':HERE.parent/'core_output/output.py',
       'tools/qualification/core_selection/check.py':HERE.parent/'core_selection/check.py',
       'tools/qualification/core_selection/after_install.py':HERE.parent/'core_selection/after_install.py',
       'tools/qualification/core_native/stage_work.py':HERE/'stage_work.py',
       'tools/qualification/core_native/verify_materials.py':HERE/'verify_materials.py'}
    for name,source in extras.items():
        target=inputs/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    verifier=load('core_bundle_verifier',HERE/'verify_materials.py')
    manifest={'schema':'qb.core-material-manifest/v1','entries':verifier.inventory(inputs,exclude_manifest=True)}
    (inputs/'material-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    verifier.verify(inputs)
    shutil.copyfile(HERE/'guest.py',work/'guest.py')
    shutil.copyfile(toolchain,work/'install-toolchain.sh')
    (work/'Dockerfile').write_text('FROM '+BASE+'\nCOPY install-toolchain.sh /install-toolchain.sh\nRUN sh /install-toolchain.sh\n')
    protocol={'schema':'qb.core-native-protocol/v1','materials_sha256':sha(inputs/'material-manifest.json'),
              'guest_sha256':sha(work/'guest.py'),'builder_files':{name:sha(work/name) for name in ('Dockerfile','install-toolchain.sh')},
              'operator_files':{name:sha(HERE.parent/name) for name in OPERATOR_FILES},
              'observation_seconds':3600,'cleanup_seconds':300,'account':'090208085542','region':'us-east-1',
              'instance_type':'m7i.large','root_gib':20,'native_qualified':False}
    (work/'protocol.json').write_text(json.dumps(protocol,sort_keys=True,indent=2)+'\n')
    # Explicit frozen public work root only; no operator state or credentials.
    with tarfile.open(output/'cpu.tar.gz','w:gz',dereference=False) as tar:
        for path in sorted(work.iterdir()):tar.add(path,arcname=path.name)
    size=(output/'cpu.tar.gz').stat().st_size
    if size>1024**3:raise ValueError('input archive byte bound')
    identity={'bytes':size,'sha256':sha(output/'cpu.tar.gz')}
    (output/'archive.json').write_text(json.dumps(identity,indent=2)+'\n')
    return dict(identity,protocol_sha256=sha(work/'protocol.json'),materials_sha256=protocol['materials_sha256'],executed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('core','dependencies','xacc','python','toolchain','output'):parser.add_argument(name,type=Path)
    args=parser.parse_args()
    print(json.dumps(package(args.core,args.dependencies,args.xacc,args.python,args.toolchain,args.output),indent=2))
