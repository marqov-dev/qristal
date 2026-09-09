"""Behavior checks for a rebuilt Core Python module; CPU qpp only."""
import json, signal, os
signal.alarm(90)
import qristal.core as q

report = {"module": os.path.realpath(q.__file__), "fixtures": []}
for name in ["zero", "x0", "x1", "double_h", "bell", "ghz", "qasm_bell", "optimized_bell"]:
    qubits = 3 if name == "ghz" else 2
    circuit = q.Circuit()
    if name == "x0": circuit.x(0)
    if name == "x1": circuit.x(1)
    if name == "double_h":
        circuit.h(0); circuit.h(0)
    if name in ("bell", "ghz", "qasm_bell", "optimized_bell"):
        circuit.h(0); circuit.cnot(0, 1)
        if name == "ghz": circuit.cnot(1, 2)
    for bit in range(qubits): circuit.measure(bit)
    session = q.session()
    session.acc = "qpp"
    session.remote_backend_database_path = "/work/qristal/qualification/empty-backends.yaml"
    session.qn = qubits
    session.sn = 4096
    session.seed = 42
    session.noplacement = True
    session.nooptimise = name != "optimized_bell"
    if name == "qasm_bell":
        session.instring = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q -> c;'
    else:
        session.irtarget = circuit
    session.run()
    raw = session.results
    counts = {"".join("1" if bit else "0" for bit in key): int(raw[key]) for key in raw}
    assert sum(counts.values()) == 4096, (name, counts)
    if name in ("bell", "ghz", "qasm_bell", "optimized_bell"):
        assert set(counts) == {"0" * qubits, "1" * qubits}, (name, counts)
        assert all(0.45 <= count / 4096 <= 0.55 for count in counts.values()), (name, counts)
    else:
        expected = {"x0": "10", "x1": "01"}.get(name, "00")
        assert counts == {expected: 4096}, (name, counts)
    report["fixtures"].append({"name": name, "counts": counts})
print("PASS: " + json.dumps(report))
