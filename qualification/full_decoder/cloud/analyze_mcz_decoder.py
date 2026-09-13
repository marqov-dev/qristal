"""Replay the experimental Decoder derivative without claiming full correctness."""
import argparse
import json
from pathlib import Path
import re
from analyze_qft import analyze as analyze_qft
from analyze_search import checkpoints

HERE=Path(__file__).resolve().parent


def analyze(root):
    root=Path(root)
    _,qft=analyze_qft(root)
    report=json.loads((root/'result.json').read_text())
    expected=json.loads((HERE/'mcz-probe-identity.json').read_text())
    if report.get('mcz_probe_identity')!=expected:raise ValueError('probe_identity')
    manifest=report['source_manifest']
    if manifest.get('variant')!='mcz-decoder':raise ValueError('probe_variant')
    hashes=manifest['source_hashes']
    if (hashes.get('qristal-core/src/algorithms/exponential_search/exponential_search.cpp')!=expected['original_sha256'] or
        hashes.get('qristal/qualification/full_decoder/cloud/direct_mcz.hpp')!=expected['header_sha256']):
        raise ValueError('probe_source_binding')
    if (report['binary_sha256'].get('exponential_search.traced.cpp')!=expected['derived_sha256'] or
        report['binary_sha256'].get('mcz-probe.patch')!=expected['patch_sha256']):
        raise ValueError('probe_output_binding')
    core=report['core_plugin_sha256']
    if report['loaded_core_libraries']!={'/work/install-xacc/plugins/libalgorithm_es.so.1.8.1':core}:
        raise ValueError('loaded_core_binding')
    stages={s['name']:s for s in report['stages']}
    for name in ('core-plugin-build','core-plugin-bundle','input-tests','tiny-build'):
        if stages[name].get('exit_code')!=0:raise ValueError('prerequisite_stage')
    if stages['input-tests']['stdout'].count('[       OK ] FullDecoderInputValidation.')!=6:
        raise ValueError('initialization_inventory')
    tiny=stages['tiny-result']
    if tiny['timeout_seconds']!=60:raise ValueError('fixture_bound')
    output=tiny.get('stdout',tiny.get('partial_stdout',''))
    points=checkpoints(output)
    completed=tiny.get('exit_code')==0 and 'PASS: caller result contract (not full Decoder correctness)' in output
    classification='not_completed'
    if completed:
        candidates=re.findall(r'OBSERVATION: tiny-oracle-candidate score=(\d+) bits=([01]+)',output)
        if len(candidates)==1 and candidates[0][1]=='1' and 1<=int(candidates[0][0])<=3:
            classification='one_oracle_consistent_candidate'
        elif 'INCONCLUSIVE: no improving candidate in four trials' in output:
            classification='caller_contract_only_no_improvement'
        else:raise ValueError('caller_observation_missing')
    return dict(classification=classification,caller_contract_completed=completed,
                full_decoder_qualified=False,prototype_only=True,
                tiny_error=tiny.get('error'),tiny_exit_code=tiny.get('exit_code'),
                checkpoints=points,last_checkpoint=points[-1],
                observed_mcz_completions=sum(p['stage']=='mcz_expand_end' for p in points),
                observed_backend_completions=sum(p['stage']=='backend_execute_end' for p in points),
                cleanup_verified=qft['cleanup_verified'],source_identity=expected)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('evidence',type=Path);args=parser.parse_args()
    summary=analyze(args.evidence)
    (args.evidence/'decoder-analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='checkpoints'},indent=2))
