"""Bind native stored-state and queue observations to console, executable, source and cleanup."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import run
from observer import console
from state_probe_analysis import parse, backend_durations
from instrument_state import HEADER_SHA, VISITOR_SHA


def analyze(root):
    root=Path(root)
    read=lambda name:json.loads((root/name).read_text())
    report,_,_=console.recover('\n'.join(read('console-filtered.json')['records']))
    if report!=read('result.json'):raise ValueError('console_result_binding')
    if report.get('kind')!='qb-sparse-state-isolated-cpu-vm' or report.get('error'):raise ValueError('native_failure')
    stages={s['name']:s for s in report['stages']}
    names=('qft-provider-build','qft-provider-resources','qft-provider-bundle','core-plugin-build','core-plugin-bundle',
           'tiny-build','baseline-sparse-build','baseline-sparse-bundle','baseline-tiny-result','neutrality-build',
           'neutrality-checks','observed-sparse-build','observed-sparse-bundle','observed-tiny-result')
    if len(stages)!=len(report['stages']) or tuple(stages)!=names:raise ValueError('stage_inventory')
    for name,item in stages.items():
        bound=180 if name.endswith('build') else (30 if name.endswith(('bundle','resources')) else 60)
        if item['timeout_seconds']!=bound:raise ValueError('stage_bound')
        timeout=name.endswith('tiny-result') and item.get('error')=='ProcessError:process_timeout'
        if item.get('exit_code')!=0 and not timeout:raise ValueError('stage_failure')
    text=lambda item:item.get('stdout',item.get('partial_stdout',''))
    neutrality=[json.loads(line.removeprefix('STATE_NEUTRALITY ')) for line in text(stages['neutrality-checks']).splitlines() if line.startswith('STATE_NEUTRALITY ')]
    if len(neutrality)!=1:raise ValueError('neutrality_inventory')
    n=neutrality[0]
    if n['cases']!=12 or not 0<n['queued_checkpoints']<=216 or not 0<=n['max_complex_difference']<1e-12:raise ValueError('neutrality_failure')
    summaries,observations=parse(text(stages['observed-tiny-result']))
    summary={'neutrality':n,'calls':summaries,'full_fixture':{}}
    for mode in ('baseline','observed'):
        item=stages[mode+'-tiny-result'];output=text(item)
        if 'LOADED_SPARSE_LIBRARY: /work/install-xacc/plugins/libsparse_simulator.so.1.8.1' not in output:raise ValueError('loaded_path')
        if item['loaded_sparse_sha256']!=report['probe_identity'][mode+'_plugin']:raise ValueError('loaded_identity')
        summary['full_fixture'][mode]={'timed_out':item.get('error')=='ProcessError:process_timeout',
          'caller_contract_passed':'PASS: caller result contract (not full Decoder correctness)' in output,
          'oracle_candidate_observed':'OBSERVATION: tiny-oracle-candidate' in output,
          **backend_durations(output)}
    sha=lambda value:bool(re.fullmatch('[a-f0-9]{64}',value))
    for name in ('tiny-smoke','state-neutrality','libsparse-baseline.so','libsparse-observed.so'):
        if not sha(report['binary_sha256'].get(name,'')):raise ValueError('binary_identity')
    identity=report['probe_identity']
    expected=json.loads((Path(__file__).parent/'state-probe-identity.json').read_text())
    if any(identity.get(k)!=v for k,v in expected.items()):raise ValueError('derived_identity')
    if identity['header_original']!=HEADER_SHA or identity['visitor_original']!=VISITOR_SHA or identity['visitor_baseline']!=VISITOR_SHA:raise ValueError('original_identity')
    for mode in ('baseline','observed'):
        if identity[mode+'_plugin']!=report['binary_sha256']['libsparse-'+mode+'.so']:raise ValueError('plugin_identity')
        if identity['visitor_'+mode]!=report['binary_sha256']['sparse-'+mode+'.cpp']:raise ValueError('visitor_identity')
    manifest=report['source_manifest']
    if manifest.get('variant') not in ('sparse-state','sparse-state-o3'):raise ValueError('source_variant')
    guest='guest_state_probe_o3.py' if manifest['variant']=='sparse-state-o3' else 'guest_state_probe.py'
    for name in (guest,'instrument_state.py','state_neutrality.cpp','patch_mcz.py','direct_mcz.hpp','tiny_profile_smoke.cpp'):
        if manifest['source_hashes'].get('qristal/qualification/full_decoder/cloud/'+name)!=hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest():raise ValueError('source_identity')
    loaded=report.get('loaded_core_libraries',{})
    if not loaded or any(d!=report['core_plugin_sha256'] for d in loaded.values()):raise ValueError('core_identity')
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
                   source_revisions=manifest['revisions'],executable_sha256=report['binary_sha256']['tiny-smoke'])
    return summary,observations

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    summary,observations=analyze(args.evidence)
    for name,value in [('analysis.json',summary),('state-observations.json',observations)]:
        (args.evidence/name).write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
