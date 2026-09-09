"""Experimental parser profile. Run only inside bounded, credential-free isolation."""
from dataclasses import dataclass
import hashlib

from adapter import validate_program


class ProgramError(ValueError):
    pass


@dataclass(frozen=True)
class PreparedProgram:
    original_sha256: str
    canonical: bytes
    qubits: int


def prepare(program, qubits):
    """Accept only X/H/CX plus complete ordered final measurement.

    Emit a fresh closed instruction set instead of passing tenant source through
    two different native parsers. This is not hosted admission or attestation.
    """
    try:
        if type(qubits) is not int or not 1 <= qubits <= 12:
            raise ValueError()
        source = validate_program(program, qubits)
        from qiskit import qasm2
        from qiskit.circuit.library import XGate, HGate, CXGate
        circuit = qasm2.loads(source, include_path=(), strict=True)
        if (len(circuit.qregs) != 1 or len(circuit.cregs) != 1
                or circuit.num_qubits != qubits or circuit.num_clbits != qubits
                or not qubits <= len(circuit.data) <= 4096):
            raise ValueError()
        gates = {XGate: ('x', 1), HGate: ('h', 1), CXGate: ('cx', 2)}
        body = []
        for item in circuit.data[:-qubits]:
            operation = item.operation
            if operation.condition is not None or item.clbits or operation.params:
                raise ValueError()
            name, arity = gates[operation.base_class]
            indices = [circuit.find_bit(bit).index for bit in item.qubits]
            if len(indices) != arity or len(set(indices)) != arity:
                raise ValueError()
            body.append(name + ' ' + ','.join(f'q[{i}]' for i in indices) + ';')
        for index, item in enumerate(circuit.data[-qubits:]):
            if (item.operation.name != 'measure' or item.operation.condition is not None
                    or len(item.qubits) != 1 or len(item.clbits) != 1
                    or circuit.find_bit(item.qubits[0]).index != index
                    or circuit.find_bit(item.clbits[0]).index != index):
                raise ValueError()
        text = '\n'.join(['OPENQASM 2.0;', 'include "qelib1.inc";',
                          f'qreg q[{qubits}];', f'creg c[{qubits}];',
                          *body, 'measure q -> c;', ''])
        canonical = text.encode('ascii')
        if len(canonical) > 65536:
            raise ValueError()
        return PreparedProgram(hashlib.sha256(program).hexdigest(), canonical, qubits)
    except Exception:
        raise ProgramError('program_rejected') from None
