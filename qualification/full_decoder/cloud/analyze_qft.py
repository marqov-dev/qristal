"""Verify a QFT experiment's saved console vectors and exact cleanup records."""
import argparse
import json
from pathlib import Path
import re

import run
from observer import console
from fourier import from_stdout, verify


def analyze(root):
    root = Path(root)
    read = lambda name: json.loads((root/name).read_text())
    report, _, _ = console.recover('\n'.join(read('console-filtered.json')['records']))
    if report != read('result.json'):
        raise ValueError('console_result_binding')
    stages = {stage['name']:stage for stage in report['stages']}
    if len(stages)!=len(report['stages']):
        raise ValueError('duplicate_stage')
    for name in ('qft-provider-build','qft-provider-resources','qft-provider-bundle','qft-check-build','qft-checks'):
        if stages.get(name,{}).get('exit_code')!=0:
            raise ValueError('qft_stage_failed')
    output = stages['qft-checks']['stdout']
    if 'PASS: 70 phase-sensitive QFT cases' not in output:
        raise ValueError('qft_pass_marker')
    records = from_stdout(output)
    summary = verify(records)
    binary = report['binary_sha256']['libmarqov_qft_qualification.so']
    if not re.fullmatch('[a-f0-9]{64}',binary) or report['loaded_qft_libraries']!={
        '/work/install-xacc/plugins/libmarqov_qft_qualification.so':binary}:
        raise ValueError('qft_library_binding')
    cleanup, resources, transfer = read('cleanup.json'),read('resources.json'),read('transfer.json')
    if (not resources['cleanup_verified'] or
        not all(cleanup[key] is True for key in ('instance_termination_observed','volumes_absent','group_absent')) or
        cleanup['instance_id']!=resources['instance'] or not resources['volumes'] or
        cleanup['volume_ids']!=resources['volumes'] or cleanup['group_id']!=resources['group'] or
        transfer.get('vm_cleanup_verified') is not True or transfer.get('transfer_cleanup_verified') is not True or transfer['cleanup_errors']):
        raise ValueError('cleanup_unverified')
    state=read('supervisor.json')
    if state['last_seen']>state['cleanup_until'] or state['plan']['run']!=transfer['run']:
        raise ValueError('run_deadline_binding')
    summary.update(provider_sha256=binary,source_revisions=report['source_manifest']['revisions'],
                   decoder_stage=stages.get('tiny-result',{}), cleanup_verified=True)
    return records,summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    args=parser.parse_args()
    records,summary=analyze(args.evidence)
    (args.evidence/'qft-vectors.json').write_text(json.dumps(records,indent=2)+'\n')
    (args.evidence/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({key:value for key,value in summary.items() if key!='decoder_stage'},indent=2))
