"""Synthetic sampling coverage study; no Qristal, Docker or cloud execution."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import random
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / "readout_mitigation" / "demo.py"
spec = importlib.util.spec_from_file_location("mitigation_core", SOURCE)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
REPEATS = 1000
SEED = 2026091301
SCENARIOS = (
    ("stationary-low", (.05, .10), (.05, .10)),
    ("stationary-medium", (.20, .10), (.20, .10)),
    ("stationary-high", (.40, .40), (.40, .40)),
    ("stale-increased", (.20, .10), (.35, .10)),
    ("stale-improved", (.20, .10), (.05, .025)),
)


def multinomial(rng, probabilities):
    remaining, mass, result = core.SHOTS, 1.0, {}
    for bits, p in list(probabilities.items())[:-1]:
        n = rng.binomialvariate(remaining, min(1.0, max(0.0, p / mass)))
        result[bits] = n
        remaining -= n
        mass -= p
    result[list(probabilities)[-1]] = remaining
    return {b: n for b, n in result.items() if n}


def wilson(successes, total):
    p, z = successes / total, 1.959963984540054
    d = 1 + z*z/total
    center = (p + z*z/(2*total))/d
    radius = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))/d
    return [center-radius, center+radius]


def analyze(records):
    expected = [(name, repeat, fixture) for name, _, _ in SCENARIOS
                for repeat in range(REPEATS) for fixture in ("zero", "bell")]
    if [(r["scenario"], r["repeat"], r["fixture"]) for r in records] != expected:
        raise ValueError("schedule")
    groups = {}
    for r in records:
        cal = core.calibrate(r["cal_zero"], r["cal_one"])
        counts = r["held_out"]
        value = core.observable(core.correct(counts, cal), "Z0Z1")
        se = core.uncertainty(counts, cal, "Z0Z1")
        # Both chosen fixtures have ideal Z0Z1 = +1.
        low, high = value-1.959963984540054*se, value+1.959963984540054*se
        groups.setdefault((r["scenario"], r["fixture"]), []).append((value, se, low <= 1 <= high))
    rows = []
    for (scenario, fixture), values in groups.items():
        covered = sum(v[2] for v in values)
        rows.append(dict(scenario=scenario, fixture=fixture, repetitions=len(values),
                         covered=covered, coverage=covered/len(values),
                         coverage_wilson95=wilson(covered,len(values)),
                         mean_bias=sum(v[0]-1 for v in values)/len(values),
                         mean_se=sum(v[1] for v in values)/len(values)))
    return rows


def generate():
    rng = random.Random(SEED)
    records = []
    for name, (a, b), (c, d) in SCENARIOS:
        for repeat in range(REPEATS):
            # Independent calibrations for every fixture and repetition.
            for fixture in ("zero", "bell"):
                zero = multinomial(rng, {"00": 1-a, "10": a})
                one = multinomial(rng, {"00": b, "10": 1-b})
                # Independent explicit forward probabilities, not core.forward().
                probs = ({"00": 1-c, "10": c} if fixture == "zero"
                         else {"00": (1-c)/2, "01": d/2, "10": c/2, "11": (1-d)/2})
                records.append(dict(scenario=name, repeat=repeat, fixture=fixture,
                                    cal_zero=zero, cal_one=one,
                                    held_out=multinomial(rng, probs)))
    return records


def main(output):
    output.mkdir()
    records = generate()
    (output/"counts.json").write_text(json.dumps(records, separators=(",",":"))+"\n")
    (output/"summary.json").write_text(json.dumps(analyze(records),indent=2)+"\n")
    manifest = dict(kind="synthetic-multinomial-coverage", native_execution=False,
                    repetitions_per_scenario_fixture=REPEATS, seed=SEED, shots=core.SHOTS,
                    python=platform.python_version(),
                    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    estimator_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()})
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(analyze(records),indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    main(parser.parse_args().output)
