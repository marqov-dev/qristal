"""Verify retained console recovery, CPU matrix and exact cleanup relationships."""
import importlib.util
import json
from pathlib import Path

import stage

spec = importlib.util.spec_from_file_location("cpu_native_checker", stage.HERE / "check_native.py")
check_native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_native)


def verify(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    expected = {'transfer.json','resources.json','cleanup.json','supervisor.json','recovered.json',
                'result.json','native-manifest.json','archive.json'}
    if manifest['schema'] != 'marqov.cpu-oci-evidence/v1' or set(manifest['files']) != expected:
        raise ValueError('evidence_set')
    for name, digest in manifest['files'].items():
        if stage.sha(root / name) != digest:
            raise ValueError('evidence_bytes')
    def read(name):
        return json.loads((root / name).read_text())
    staging = json.loads((stage.HERE.parent / 'evidence/2026-09-13-cpu-staging/observation.json').read_text())
    if read('native-manifest.json')['context_sha256'] != staging['context_record_sha256']:
        raise ValueError('prior_staging_binding')
    for name, path in {'Dockerfile':stage.HERE / 'Dockerfile', 'apt-runtime.txt':stage.HERE.parent / 'runtime/apt-runtime.txt'}.items():
        if stage.sha(path) != staging['context']['files'][name]:
            raise ValueError('recipe_binding')
    report = read('result.json')
    recovered = read('recovered.json')
    spec = importlib.util.spec_from_file_location('cpu_evidence_console', stage.HERE.parent / 'gpu_package/console.py')
    console = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(console)
    observed, _, _ = console.recover('\n'.join(recovered['complete_records']))
    if observed != report or recovered['result'] != report:
        raise ValueError('console_binding')
    verdict = check_native.verify(report, read('native-manifest.json'))
    resources, cleanup, supervisor, transfer = [read(n + '.json') for n in ('resources','cleanup','supervisor','transfer')]
    if (resources['instance'] != cleanup['instance_id'] or resources['group'] != cleanup['group_id']
            or resources['volumes'] != cleanup['volume_ids'] or not resources['volumes']
            or resources['group'] != supervisor['plan']['group'] or resources['group'] != transfer['group']
            or transfer['artifact'] != read('archive.json')):
        raise ValueError('cleanup_identity')
    if any(transfer[key] != supervisor['plan'][key] for key in ('account','region','run')):
        raise ValueError('lifecycle_plan_binding')
    if (not supervisor['launch_attempted'] or supervisor['last_instance_state'] != 'terminated'
            or not resources['cleanup_verified'] or supervisor['phase'] != 'cleaned'
            or supervisor['last_seen'] > supervisor['cleanup_until']
            or not cleanup['instance_termination_observed'] or not cleanup['volumes_absent']
            or not cleanup['group_absent'] or cleanup['no_launch_attempted']
            or not transfer['vm_cleanup_verified'] or not transfer['transfer_cleanup_verified']
            or transfer['cleanup_errors'] or transfer.get('error')):
        raise ValueError('cleanup_incomplete')
    verdict['cleanup_verified'] = True
    verdict['gpu_backend_rejection_verified'] = False
    return verdict


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1])), indent=2))
