"""Validate untrusted local CLI output; no hosted receipt or provenance authority."""
from dataclasses import dataclass
import hashlib
import json

MAX_OUTPUT_BYTES = 131072


class CandidateError(ValueError):
    """Static diagnostic; never includes candidate contents."""


def require(ok):
    if not ok:
        raise CandidateError('candidate_rejected')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def reject_constant(value):
    raise CandidateError('candidate_rejected')


@dataclass(frozen=True)
class LocalCounts:
    """Content-checked local counts, not an authenticated execution result."""
    program_sha256: str
    backend: str
    shots: int
    counts: tuple[tuple[str, int], ...]
    logical_bits: tuple[str, ...]


def validate_candidate(raw, *, returncode, program, backend, qubits, shots):
    try:
        require(type(returncode) is int and returncode == 0)
        require(type(program) is bytes and 0 < len(program) <= 65536)
        require(type(backend) is str and backend in ('qpp', 'aer'))
        require(type(qubits) is int and 1 <= qubits <= 12)
        require(type(shots) is int and 1 <= shots <= 16384)
        require(type(raw) is bytes and 0 < len(raw) <= MAX_OUTPUT_BYTES + 1)
        # The wire format allows exactly one terminal CLI newline, no other tail.
        payload = raw[:-1] if raw.endswith(b'\n') else raw
        require(0 < len(payload) <= MAX_OUTPUT_BYTES)
        require(payload.startswith(b'{') and payload.endswith(b'}'))
        obj = json.loads(payload.decode('utf-8'), object_pairs_hook=unique_object,
                         parse_constant=reject_constant)
        require(type(obj) is dict and set(obj) == {
            'interface', 'program_sha256', 'backend', 'shots', 'bit_order', 'counts'})
        digest = hashlib.sha256(program).hexdigest()
        require(obj['interface'] == 'local-qristal-sample/experimental')
        require(obj['program_sha256'] == digest and obj['backend'] == backend)
        require(type(obj['shots']) is int and obj['shots'] == shots)
        require(obj['bit_order'] == 'qubit_0_first')
        counts = obj['counts']
        require(type(counts) is dict and 0 < len(counts) <= 2**qubits)
        for label, count in counts.items():
            require(len(label) == qubits and all(bit in '01' for bit in label))
            require(type(count) is int and 0 < count <= shots)
        require(sum(counts.values()) == shots)
        return LocalCounts(digest, backend, shots, tuple(sorted(counts.items())),
                           tuple(f'q[{i}]' for i in range(qubits)))
    except Exception:
        raise CandidateError('candidate_rejected') from None
