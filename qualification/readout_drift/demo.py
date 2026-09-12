"""Predeclared stale versus refreshed calibration experiment."""
import hashlib
import importlib.util
import json
from pathlib import Path

core_path = Path(__file__).with_name("mitigation_core.py")
if not core_path.exists():
    core_path = Path(__file__).resolve().parent.parent / "readout_mitigation" / "demo.py"
spec = importlib.util.spec_from_file_location("mitigation_core", core_path)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
POINTS = ((.20, .10), (.25, .10), (.35, .10), (.10, .20), (.05, .025))


def schedule():
    items = []
    for setting, (a, b) in enumerate(POINTS):
        cases = [('calibration', 'zero'), ('calibration', 'x0')]
        cases += [('held_out', f) for f in core.FIXTURES]
        for index, (role, fixture) in enumerate(cases):
            items.append(dict(id=f'{setting}:{role}:{fixture}', setting=setting,
                              role=role, fixture=fixture,
                              program=core.HEADER + core.FIXTURES[fixture][0] + 'measure q -> c;',
                              options=dict(qubits=2, shots=core.SHOTS, seed=22001+100*setting+index,
                                           readout=dict(p10=a, p01=b))))
    return items


def analyze(report):
    if report.get('schema') != 'qb-readout-drift-v1':
        raise ValueError('schema')
    expected = schedule()
    records = report['records']
    if len(records) != len(expected):
        raise ValueError('schedule')
    for r, e in zip(records, expected):
        if any(r.get(k) != v for k, v in e.items()):
            raise ValueError('binding')
        if (r['backend'] != 'aer'
                or r['program_sha256'] != hashlib.sha256(e['program'].encode()).hexdigest()
                or r['options_sha256'] != hashlib.sha256(
                    json.dumps(e['options'], sort_keys=True).encode()).hexdigest()):
            raise ValueError('hash_binding')
        observed = core.distribution(r['counts'])
        model = core.forward(core.FIXTURES[r['fixture']][1], *POINTS[r['setting']])
        if any(abs(observed[b]-model[b]) > (0 if model[b] == 0 else .025) for b in core.BITS):
            raise ValueError('raw_model')
    by_id = {r['id']: r for r in records}
    calibrations = [core.calibrate(by_id[f'{s}:calibration:zero']['counts'],
                                  by_id[f'{s}:calibration:x0']['counts'])
                    for s in range(len(POINTS))]
    outcomes, settings = [], []
    for s in range(len(POINTS)):
        errors = {k: [] for k in ('raw', 'stale', 'fresh')}
        for name, (_, ideal) in core.FIXTURES.items():
            counts = by_id[f'{s}:held_out:{name}']['counts']
            probs = {'raw': core.distribution(counts),
                     'stale': core.correct(counts, calibrations[0]),
                     'fresh': core.correct(counts, calibrations[s])}
            if any(abs(probs['fresh'][b]-ideal.get(b, 0)) > .08 for b in core.BITS):
                raise ValueError('fresh_probability')
            for obs in ('Z0', 'Z0Z1'):
                target = core.observable(ideal, obs)
                values = {k: core.observable(p, obs) for k, p in probs.items()}
                for k, v in values.items():
                    errors[k].append(abs(v-target))
                outcomes.append(dict(setting=s, fixture=name, observable=obs, ideal=target,
                                     **values, stale_se=core.uncertainty(counts, calibrations[0], obs),
                                     fresh_se=core.uncertainty(counts, calibrations[s], obs)))
        means = {k: sum(v)/len(v) for k, v in errors.items()}
        if means['fresh'] > .5*means['raw']:
            raise ValueError('fresh_improvement')
        settings.append(dict(setting=s, readout=list(POINTS[s]), calibration=calibrations[s], mae=means))
    return dict(settings=settings, outcomes=outcomes)


def main():
    from local_pipeline import run_readout
    records = []
    for item in schedule():
        result = run_readout(item['program'].encode(),
                             json.dumps(item['options'], sort_keys=True).encode())
        if result.result.program_sha256 != result.canonical_program_sha256:
            raise ValueError('canonical_binding')
        records.append(dict(item, program_sha256=result.original_program_sha256,
                            options_sha256=result.options_sha256, backend=result.result.backend,
                            counts=dict(result.result.counts)))
    report = dict(schema='qb-readout-drift-v1', records=records)
    analyze(report)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
