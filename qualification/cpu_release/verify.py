"""Bind acquired CPU tests, inventory and attestations to registry identity."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

sys.path.insert(0,str(HERE.parent/'cpu_package'))
native=load('cpu_command_contract',HERE.parent/'cpu_package/check_native.py')
attest=load('cpu_attestations',HERE.parent/'gpu_release/attestations.py')


def read_inputs():return json.loads((HERE/'inputs.json').read_text())


def verify(root):
    def read(name):return json.loads((root/name).read_text())
    def digest(name):return 'sha256:'+hashlib.sha256((root/name).read_bytes()).hexdigest()
    release=read('release.json'); context=read('release-context.json'); index=read('registry-index.json')
    if (release['schema']!='marqov.cpu-release/v1' or release['status']!='published_candidate_pending_acquired_checks'
            or release['hosted_available'] is not False or context['schema']!='marqov.cpu-release-context/v1'
            or context['parent']!=read_inputs()
            or context['matrix_sha256']!=hashlib.sha256((HERE/'matrix.py').read_bytes()).hexdigest()
            or context['inventory_sha256']!=hashlib.sha256((HERE/'inventory.py').read_bytes()).hexdigest()):raise ValueError('release_source_binding')
    image=release['image']; configuration=read('image-inspect.json')[0]
    selected=[m for m in index['manifests'] if m.get('platform',{}).get('os')=='linux' and m.get('platform',{}).get('architecture')=='amd64']
    if (image != 'ghcr.io/marqov-dev/qristal-cpu@'+digest('registry-index.json') or len(selected)!=1
            or selected[0]['digest'] != digest('platform-manifest.json')
            or read('platform-manifest.json')['config']['digest'] != configuration['Id']
            or read('build-metadata.json')['containerimage.digest'] != digest('registry-index.json')
            or release['context'] != context or release['source_revision'] != context['source_revision']):
        raise ValueError('registry_binding')
    tests=read('acquired/image-tests.json'); image_id=configuration['Id']
    expected={'capabilities','core','noise','integration','decoder','bell','noisy-bell','reject-shots','reject-gpu','isolation'}
    if tests['image']!=image_id or tests['no_host_mounts'] is not True or len(tests['tests'])!=10 or {t['name'] for t in tests['tests']}!=expected:
        raise ValueError('matrix_identity')
    for test in tests['tests']:
        command=test['command']; container=command[4] if len(command)>4 else ''
        if not re.fullmatch('marqov-runtime-test-[a-f0-9]{10}',container):raise ValueError('container_name')
        expected_command=native.expected_command(test['name'],container,image_id)
        if test['name']=='reject-gpu':expected_command=expected_command[:-2]+['--qasm','/checks/bell.qasm','--backend','gpu']
        if command!=expected_command or test['exit']!=(2 if test['name'].startswith('reject-') else 0):raise ValueError('matrix_command')
    if (root/'acquired/image-reject-gpu.log').read_text().strip()!='qristal_sample_failed:backend':
        raise ValueError('backend_rejection_not_observed')
    inventory=read('inventory.json')
    if (inventory['uid']!=65532 or inventory['architecture']!='x86_64'
            or inventory['payload']['inventory.py']!=context['inventory_sha256']
            or any(not inventory['python_environments'][e] for e in ('core','integrations'))
            or not inventory['dpkg'] or not inventory['notices']):raise ValueError('inventory')
    for name in ('runtime.py','adapter.py','capabilities.json'):
        if inventory['payload'][name]!=context['payload_hashes'][name]:raise ValueError('payload')
    config=configuration['Config']
    if (config['User']!='65532:65532' or config['Entrypoint']!=['python3','/opt/qristal/runtime.py']
            or config['Cmd']!=['--capabilities'] or config['WorkingDir']!='/tmp'
            or config['Labels']['org.opencontainers.image.source']!='https://github.com/marqov-dev/qristal'
            or config['Labels']['org.opencontainers.image.revision']!=release['source_revision']):raise ValueError('runtime_configuration')
    sbom,provenance=read('sbom.json'),read('provenance.json');attest.check(sbom,provenance)
    slsa=attest.document(provenance,'SLSA')
    args=slsa['buildDefinition']['externalParameters']['request']['root']['request']['args']
    if args['vcs:revision']!=release['source_revision'] or args['vcs:source']!='https://github.com/marqov-dev/qristal' or slsa['runDetails']['builder']['id']!=release['workflow_run']:
        raise ValueError('provenance_source')
    return {'schema':'marqov.cpu-acquired-qualification/v1','registry_image':image,'configuration':image_id,
            'native_passed':True,'backend_rejection_verified':True,'inventory_exported':True,'attestations':'extracted_predicates_checked_not_raw_subject_binding','hosted_available':False}


if __name__=='__main__':
    root=Path(sys.argv[1]);result=verify(root)
    (root/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
