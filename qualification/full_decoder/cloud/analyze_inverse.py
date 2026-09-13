"""Bind native controlled inverse observations to console, executable, source and cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import run
from observer import console
from inverse_oracle import verify, verify_sparse


def analyze(root):
    root=Path(root)
    read=lambda name:json.loads((root/name).read_text())
    report,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
    if report!=read('result.json'):raise ValueError('console_result_binding')
    if report.get('kind')!='qb-inverse-isolated-cpu-vm' or report.get('error'):raise ValueError('native_failure')
    stages={s['name']:s for s in report['stages']}
    if len(stages)!=len(report['stages']) or set(stages)!=set(('inverse-build','inverse-negative','inverse-qpp','inverse-sparse')):
        raise ValueError('stage_inventory')
    for name,stage in stages.items():
        if stage.get('exit_code')!=0:raise ValueError('stage_failure')
        if stage['timeout_seconds']!=(180 if name=='inverse-build' else 60):raise ValueError('stage_bound')
    if 'PASS: 12 inverse rejected inputs' not in stages['inverse-negative']['stdout']:
        raise ValueError('negative_gate')
    if 'PASS: 140 controlled inverse complex-state cases plus 20 legacy fallback observations' not in stages['inverse-qpp']['stdout']:
        raise ValueError('state_pass_marker')
    if 'PASS: 20 sparse controlled inverse roundtrips, each repeated twice' not in stages['inverse-sparse']['stdout']:
        raise ValueError('sparse_pass_marker')
    states=[json.loads(line[len('INVERSE_CASE '):]) for line in stages['inverse-qpp']['stdout'].splitlines() if line.startswith('INVERSE_CASE ')]
    sparse=[json.loads(line[len('INVERSE_SPARSE '):]) for line in stages['inverse-sparse']['stdout'].splitlines() if line.startswith('INVERSE_SPARSE ')]
    summary={'qpp':verify(states),'sparse_native_roundtrips':20,'sparse_interference':verify_sparse(sparse),'rejected_inputs':12}
    sha=lambda value:bool(re.fullmatch('[a-f0-9]{64}',value))
    if not sha(report['binary_sha256'].get('inverse-checks','')):raise ValueError('binary_identity')
    manifest=report['source_manifest']
    if manifest.get('variant')!='structured-inverse':raise ValueError('source_variant')
    for name in ('inverse_checks.cpp','direct_mcz.hpp','structured_inverse.hpp','guest_inverse.py'):
        if manifest['source_hashes'].get('qristal/qualification/full_decoder/cloud/'+name)!=hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest():
            raise ValueError('source_identity')
    observed=set()
    for stage in stages.values():
        for line in stage.get('stdout','').splitlines():
            if line.startswith('LOADED_RUNTIME_LIBRARY: '):observed.add(line.removeprefix('LOADED_RUNTIME_LIBRARY: '))
    libraries=report.get('loaded_runtime_libraries',{})
    if not observed or set(libraries)!=observed or not all(path.startswith('/work/') and sha(digest) for path,digest in libraries.items()):
        raise ValueError('runtime_identity')
    cleanup,resources,transfer=read('cleanup.json'),read('resources.json'),read('transfer.json')
    if (not resources['cleanup_verified'] or not all(cleanup[k] is True for k in ('instance_termination_observed','volumes_absent','group_absent')) or
        cleanup['instance_id']!=resources['instance'] or not resources['volumes'] or cleanup['volume_ids']!=resources['volumes'] or
        cleanup['group_id']!=resources['group'] or transfer.get('vm_cleanup_verified') is not True or
        transfer.get('transfer_cleanup_verified') is not True or transfer['cleanup_errors']):
        raise ValueError('cleanup_unverified')
    supervisor=read('supervisor.json')
    if supervisor['last_seen']>supervisor['cleanup_until'] or supervisor['plan']['run']!=transfer['run']:
        raise ValueError('deadline_binding')
    if read('archive.json')!=transfer['artifact']:raise ValueError('archive_binding')
    summary.update(cleanup_verified=True,full_decoder_qualified=False,prototype_only=True,
                   source_revisions=manifest['revisions'],executable_sha256=report['binary_sha256']['inverse-checks'])
    return summary,states,sparse

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    summary,states,sparse=analyze(args.evidence)
    for name,value in [('analysis.json',summary),('complex-states.json',states),('sparse-interference-counts.json',sparse)]:
        (args.evidence/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
