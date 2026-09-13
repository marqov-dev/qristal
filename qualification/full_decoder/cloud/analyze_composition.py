"""Bind native phase composition and construction inventory to console, executable, source and cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import run
from observer import console
from composition_oracle import verify_states, verify_inventory


def analyze(root):
    root=Path(root)
    read=lambda name:json.loads((root/name).read_text())
    report,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
    if report!=read('result.json'):raise ValueError('console_result_binding')
    if report.get('kind')!='qb-phase-composition-isolated-cpu-vm' or report.get('error'):raise ValueError('native_failure')
    stages={s['name']:s for s in report['stages']}
    bounds={'qft-provider-build':180,'qft-provider-resources':30,'qft-provider-bundle':30,
            'composition-build':180,'composition-checks':60,'inventory-build':180,'inventory-checks':60}
    if len(stages)!=len(report['stages']) or set(stages)!=set(bounds):raise ValueError('stage_inventory')
    for name,stage in stages.items():
        if stage.get('exit_code')!=(1 if name=='inventory-checks' else 0):raise ValueError('stage_failure')
        if stage['timeout_seconds']!=bounds[name]:raise ValueError('stage_bound')
    if 'PASS: 4 candidate interference checks; 4 legacy composition observations' not in stages['composition-checks']['stdout']:
        raise ValueError('composition_marker')
    inventory=stages['inventory-checks']
    if (report.get('inventory_intentional_stop') is not True or
        'PREPARATION_INVENTORY_COMPLETE: construction only; no search or simulation' not in inventory['stdout'] or
        'QB_INVENTORY_ONLY_STOP' not in inventory['stderr']):raise ValueError('intentional_stop')
    states=[json.loads(line.removeprefix('COMPOSITION ')) for line in stages['composition-checks']['stdout'].splitlines() if line.startswith('COMPOSITION ')]
    counts=[json.loads(line.removeprefix('PREPARATION_INVENTORY ')) for line in inventory['stdout'].splitlines() if line.startswith('PREPARATION_INVENTORY ')]
    summary={'composition':verify_states(states),'inventory':verify_inventory(counts)}
    sha=lambda value:bool(re.fullmatch('[a-f0-9]{64}',value))
    if not all(sha(report['binary_sha256'].get(name,'')) for name in ('composition-checks','inventory-checks','libmarqov_qft_qualification.so')):raise ValueError('binary_identity')
    manifest=report['source_manifest']
    if manifest.get('variant')!='phase-composition':raise ValueError('source_variant')
    for name in ('inverse_checks.cpp','direct_mcz.hpp','structured_inverse.hpp','guest_phase_composition.py','phase_composition_checks.cpp','preparation_inventory.hpp','instrument_preparation.py'):
        if manifest['source_hashes'].get('qristal/qualification/full_decoder/cloud/'+name)!=hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest():
            raise ValueError('source_identity')
    identity=report['inventory_source_identity']
    original=manifest['source_hashes']['qristal-decoder/src/quantum_decoder.cpp']
    if identity['original_sha256']!=original or identity['derived_sha256']!=report['binary_sha256']['quantum_decoder.inventory.cpp']:
        raise ValueError('derived_source_binding')
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
                   source_revisions=manifest['revisions'],executable_sha256=report['binary_sha256']['composition-checks'])
    return summary,states,counts

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    summary,states,counts=analyze(args.evidence)
    for name,value in [('analysis.json',summary),('complex-states.json',states),('preparation-inventory.json',counts)]:
        (args.evidence/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
