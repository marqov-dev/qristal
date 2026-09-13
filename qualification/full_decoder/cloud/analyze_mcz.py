"""Bind native MCZ observations to console, executable, source and cleanup."""
import argparse
import json
from pathlib import Path
import re
import run
from observer import console
from mcz_oracle import verify_states, verify_sparse


def analyze(root):
    root=Path(root)
    read=lambda name:json.loads((root/name).read_text())
    report,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
    if report!=read('result.json'):raise ValueError('console_result_binding')
    if report.get('kind')!='qb-mcz-isolated-cpu-vm' or report.get('error'):raise ValueError('native_failure')
    stages={s['name']:s for s in report['stages']}
    if len(stages)!=len(report['stages']) or set(stages)!=set(('mcz-build','mcz-negative','mcz-qpp','mcz-sparse')):
        raise ValueError('stage_inventory')
    for name,stage in stages.items():
        if stage.get('exit_code')!=0:raise ValueError('stage_failure')
        if stage['timeout_seconds']!=(180 if name=='mcz-build' else 60):raise ValueError('stage_bound')
    if 'PASS: 10 MCZ rejected inputs and clone enabled-state checks' not in stages['mcz-negative']['stdout']:
        raise ValueError('negative_gate')
    if 'PASS: 42 MCZ complex-state cases, each repeated twice' not in stages['mcz-qpp']['stdout']:
        raise ValueError('state_pass_marker')
    if 'PASS: 158 MCZ sparse interference cases, each repeated twice' not in stages['mcz-sparse']['stdout']:
        raise ValueError('sparse_pass_marker')
    states=[json.loads(line[len('MCZ_STATE '):]) for line in stages['mcz-qpp']['stdout'].splitlines() if line.startswith('MCZ_STATE ')]
    sparse=[json.loads(line[len('MCZ_SPARSE '):]) for line in stages['mcz-sparse']['stdout'].splitlines() if line.startswith('MCZ_SPARSE ')]
    summary={'qpp':verify_states(states),'sparse':verify_sparse(sparse),'rejected_inputs':10}
    sha=lambda value:bool(re.fullmatch('[a-f0-9]{64}',value))
    if not sha(report['binary_sha256'].get('mcz-checks','')):raise ValueError('binary_identity')
    manifest=report['source_manifest']
    if manifest.get('variant')!='mcz':raise ValueError('source_variant')
    for name in ('mcz_checks.cpp','direct_mcz.hpp','guest_mcz.py'):
        if not sha(manifest['source_hashes'].get('qristal/qualification/full_decoder/cloud/'+name,'')):
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
                   source_revisions=manifest['revisions'],executable_sha256=report['binary_sha256']['mcz-checks'])
    return summary,states,sparse

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    summary,states,sparse=analyze(args.evidence)
    for name,value in [('analysis.json',summary),('complex-states.json',states),('sparse-counts.json',sparse)]:
        (args.evidence/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
