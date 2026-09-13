"""Replay a source-bound native trace; never infer algorithm correctness."""
import argparse
import json
from pathlib import Path
import re

from analyze_qft import analyze as analyze_qft

HERE = Path(__file__).resolve().parent
PATTERN = re.compile(r'^SEARCH_TRACE ([a-z_]+) elapsed_ms=(\d+) count=(-?\d+)$')


def checkpoints(output):
    points = []
    previous = 0
    for line in output.splitlines():
        if not line.startswith('SEARCH_TRACE '):
            continue
        match = PATTERN.fullmatch(line)
        if not match:
            raise ValueError('malformed_trace')
        name, elapsed, count = match.groups()
        elapsed = int(elapsed)
        if name == 'execute_begin':
            previous = 0
        if elapsed < previous:
            raise ValueError('nonmonotonic_trace')
        previous = elapsed
        points.append(dict(stage=name, elapsed_ms=elapsed, count=int(count)))
    if not points:
        raise ValueError('missing_trace')
    return points


def analyze(root):
    root = Path(root)
    vectors, _ = analyze_qft(root)  # Console checksum, Fourier values and exact cleanup.
    report = json.loads((root/'result.json').read_text())
    expected = json.loads((HERE/'search-trace-identity.json').read_text())
    if report.get('search_trace_identity') != expected:
        raise ValueError('trace_source_identity')
    source = 'qristal-core/src/algorithms/exponential_search/exponential_search.cpp'
    if report['source_manifest']['source_hashes'].get(source) != expected['source_sha256']:
        raise ValueError('trace_input_binding')
    if report['binary_sha256'].get('exponential_search.traced.cpp') != expected['traced_sha256']:
        raise ValueError('trace_output_binding')
    if report['binary_sha256'].get('search-trace.patch') != expected['patch_sha256']:
        raise ValueError('trace_patch_binding')
    core = report['core_plugin_sha256']
    if report.get('loaded_core_libraries') != {
        '/work/install-xacc/plugins/libalgorithm_es.so.1.8.1': core}:
        raise ValueError('loaded_core_binding')
    stages = {item['name']:item for item in report['stages']}
    tests = stages.get('input-tests', {})
    if tests.get('exit_code') != 0 or tests.get('stdout','').count('[       OK ] FullDecoderInputValidation.') != 6:
        raise ValueError('initialization_gate')
    tiny = stages['tiny-result']
    points = checkpoints(tiny.get('stdout', tiny.get('partial_stdout', '')))
    return dict(checkpoints=points, last_checkpoint=points[-1],
                tiny_error=tiny.get('error'), tiny_exit_code=tiny.get('exit_code'),
                tiny_timeout_seconds=tiny['timeout_seconds'],
                qft_cases=len(vectors),
                cleanup_verified=True, full_decoder_qualified=False,
                source_identity=expected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    args = parser.parse_args()
    result = analyze(args.evidence)
    (args.evidence/'search-analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
