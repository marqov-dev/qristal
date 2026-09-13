"""Replay source-bound diagnostic timings; never promote a Decoder timeout."""
import argparse
import hashlib
from collections import defaultdict
import json
from pathlib import Path
import re
from analyze_mcz_decoder import analyze as decoder

HERE=Path(__file__).resolve().parent
POINT=re.compile(r'SPARSE_PROFILE (begin|progress|phase_end|sample_begin|sample_end) elapsed_us=(\d+) phase=(\d+) nodes=(\d+) enabled=(\d+) accepts=(\d+)')
COST=re.compile(r'SPARSE_COST phase=(\d+) gate=(\S+) calls=(\d+) accept_ns=(\d+)')

def parse(output):
    calls=[];current=None
    for line in output.splitlines():
        if line.startswith('SPARSE_PROFILE '):
            match=POINT.fullmatch(line)
            if not match:raise ValueError('malformed_profile')
            event,*numbers=match.groups()
            point=dict(zip(('elapsed_us','phase','nodes','enabled','accepts'),map(int,numbers)),event=event)
            if event=='begin':
                current={'points':[],'costs':[]};calls.append(current)
            if current is None:raise ValueError('missing_profile_begin')
            previous=current['points'][-1] if current['points'] else None
            if previous and any(point[k]<previous[k] for k in ('elapsed_us','phase','nodes','enabled','accepts')):
                raise ValueError('nonmonotonic_profile')
            if not point['accepts']<=point['enabled']<=point['nodes']:raise ValueError('invalid_profile_counts')
            current['points'].append(point)
        elif line.startswith('SPARSE_COST '):
            match=COST.fullmatch(line)
            if not match or current is None:raise ValueError('malformed_cost')
            phase,gate,count,ns=match.groups()
            if int(phase)!=current['points'][-1]['phase']:raise ValueError('cost_phase')
            current['costs'].append(dict(phase=int(phase),gate=gate,calls=int(count),accept_ns=int(ns)))
    if not calls:raise ValueError('missing_profile')
    for call in calls:
        sums=defaultdict(lambda:dict(calls=0,accept_ns=0))
        for cost in call['costs']:
            for key in ('calls','accept_ns'):sums[cost['gate']][key]+=cost[key]
        call['totals_by_gate']=dict(sums)
        last=call['points'][-1]
        if sum(v['calls'] for v in sums.values())!=last['accepts']:raise ValueError('cost_count_binding')
        call['sampling_completed']=last['event']=='sample_end'
    return calls

def analyze(root):
    root=Path(root)
    summary=decoder(root,expected_variant='backend-profile')
    report=json.loads((root/'result.json').read_text())
    identity=json.loads((HERE/'sparse-profile-identity.json').read_text())
    if report.get('sparse_profile_identity')!=identity:raise ValueError('sparse_source_identity')
    if report['source_manifest']['source_hashes'].get('qristal-core/src/backends/sims/microsoft/sparse-sim/SparseStateVecAccelerator.cpp')!=identity['source_sha256']:
        raise ValueError('sparse_source_binding')
    for name,key in (('SparseStateVecAccelerator.profile.cpp','derived_sha256'),('sparse-profile.patch','patch_sha256')):
        if report['binary_sha256'].get(name)!=identity[key]:raise ValueError('sparse_output_binding')
    fixture=hashlib.sha256((HERE/'tiny_profile_smoke.cpp').read_bytes()).hexdigest()
    if report['source_manifest']['source_hashes'].get('qristal/qualification/full_decoder/cloud/tiny_profile_smoke.cpp')!=fixture:
        raise ValueError('profile_fixture_binding')
    binary=report['sparse_plugin_sha256']
    if not re.fullmatch('[a-f0-9]{64}',binary) or report['binary_sha256'].get('libsparse_simulator.so.1.8.1')!=binary or report['loaded_sparse_libraries']!={'/work/install-xacc/plugins/libsparse_simulator.so.1.8.1':binary}:
        raise ValueError('loaded_sparse_binding')
    stages={s['name']:s for s in report['stages']}
    for name in ('sparse-plugin-build','sparse-plugin-bundle'):
        if stages[name].get('exit_code')!=0:raise ValueError('sparse_build_failed')
    tiny=stages['tiny-result']
    calls=parse(tiny.get('stdout',tiny.get('partial_stdout','')))
    summary.update(backend_calls=calls,sparse_identity=identity,sparse_plugin_sha256=binary,
                   timing_is_diagnostic=True,amplitude_counts_measured=False)
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    result=analyze(args.evidence)
    (args.evidence/'backend-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('backend_calls','checkpoints')},indent=2))
