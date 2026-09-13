"""Native-only installed Core fixture, never part of offline discovery."""
from pathlib import Path
import qristal.core

module = Path(qristal.core.__file__).resolve()
assert module.is_relative_to(Path('/work/install-core/lib/qristal'))
print('CORE_PY_MODULE', module)
for bell in (False, True):
    sim = qristal.core.session()
    sim.qn, sim.sn, sim.acc = 2, 256, 'qpp'
    sim.noplacement = sim.nooptimise = True
    sim.instring = ('__qpu__ void probe(qreg q) { OPENQASM 2.0; include "qelib1.inc"; creg c[2]; '
                   + ('h q[0]; cx q[0], q[1]; ' if bell else '')
                   + 'measure q[0] -> c[0]; measure q[1] -> c[1]; }')
    sim.run()
    counts = {}
    result = sim.results
    for bits in result:
        count = result[bits]
        bits = tuple(bits)
        assert len(bits) == 2 and all(bit in (False, True) for bit in bits)
        assert isinstance(count, int) and not isinstance(count, bool) and count >= 0
        key = ''.join('1' if bit else '0' for bit in bits)
        counts[key] = counts.get(key, 0) + count
    assert sum(counts.values()) == 256
    assert set(counts) == ({'00', '11'} if bell else {'00'})
    assert all(value > 0 for value in counts.values())
    print('CORE_PY', 'bell' if bell else 'identity', counts)
print('PASS: installed Core Python QPP identity and Bell')
