"""Analytic CPU Aer noise fixtures. No device models or remote services."""
import json, os, signal
signal.alarm(180)
import qristal.core as q

SHOTS = 16384
report = {"module": os.path.realpath(q.__file__), "shots": SHOTS, "tolerance": 0.025, "fixtures": []}

def run(name, gates, expected, readout=None, channel=None, qubits=1):
    s = q.session()
    s.acc = "aer"
    s.qn = qubits
    s.sn = SHOTS
    s.seed = 42
    s.aer_omp_threads = 2
    s.noplacement = True
    s.nooptimise = True
    s.remote_backend_database_path = "/work/qristal/qualification/empty-backends.yaml"
    s.instring = f'OPENQASM 2.0; include "qelib1.inc"; qreg q[{qubits}]; creg c[{qubits}]; {gates} measure q -> c;'
    if readout is not None or channel is not None:
        nm = q.NoiseModel()
        nm.name = "community_analytic_fixture"
        if readout is not None:
            ro = q.ReadoutError()
            # P(report 1 | prepared 0), P(report 0 | prepared 1).
            ro.p_10, ro.p_01 = readout
            nm.set_qubit_readout_error(0, ro)
        if channel is not None:
            # The default Qobj compiler represents X as one u3 operation.
            nm.add_gate_error(channel, "u3", [0])
        s.noise = True
        s.noise_model = nm
    else:
        s.noise = False
    s.run()
    raw = s.results
    counts = {"".join("1" if b else "0" for b in key): int(raw[key]) for key in raw}
    assert sum(counts.values()) == SHOTS, (name, counts)
    assert not set(counts) - set(expected), (name, counts)
    for bits, probability in expected.items():
        actual = counts.get(bits, 0) / SHOTS
        tolerance = 0 if probability in (0, 1) else 0.025
        assert abs(actual - probability) <= tolerance, (name, bits, actual, probability)
    report["fixtures"].append({"name": name, "counts": counts, "expected": expected})

run("ideal_zero", "id q[0];", {"0": 1})
run("ideal_one", "x q[0];", {"1": 1})
run("readout_zero", "id q[0];", {"0": .8, "1": .2}, readout=(.2, .1))
run("readout_one", "x q[0];", {"0": .1, "1": .9}, readout=(.2, .1))
run("readout_flip_zero", "id q[0];", {"1": 1}, readout=(1., 1.))
run("readout_flip_one", "x q[0];", {"0": 1}, readout=(1., 1.))
run("readout_bell", "h q[0]; cx q[0],q[1];", {"00": .4, "10": .1, "11": .45, "01": .05}, readout=(.2, .1), qubits=2)
run("amplitude_damping", "x q[0];", {"0": .25, "1": .75}, channel=q.AmplitudeDampingChannel.Create(0, .25))
run("complete_amplitude_damping", "x q[0];", {"0": 1}, channel=q.AmplitudeDampingChannel.Create(0, 1.))
# Symmetric Pauli noise: X or Y flips |1>, each with probability p/3.
run("depolarizing", "x q[0];", {"0": .2, "1": .8}, channel=q.DepolarizingChannel.Create(0, .3))
print("PASS: " + json.dumps(report))
