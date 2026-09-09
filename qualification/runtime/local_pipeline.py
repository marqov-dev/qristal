"""Local experiment only: run inside the qualified, credential-free container.

Returned hashes describe this local observation. They are not trusted provenance,
attestation, a hosted artifact, or permission to promote customer state.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from adapter import validate_options
from bounded_process import capture
from candidate import LocalCounts, unique_object, reject_constant, validate_candidate
from program_guard import prepare


class PipelineError(ValueError):
    pass


@dataclass(frozen=True)
class LocalObservation:
    original_program_sha256: str
    canonical_program_sha256: str
    options_sha256: str
    result: LocalCounts


def run_local(program, options, *, backend='qpp'):
    """Join parsing, fixed CLI execution and candidate validation; ideal only.

    options are bounded JSON bytes with exactly integer qubits, shots and seed.
    An outer isolation/deadline boundary must cover this entire call, including
    parsing. The inner deadline covers only the simulation subprocess.
    """
    try:
        if type(options) is not bytes or not 0 < len(options) <= 1024:
            raise ValueError()
        settings = json.loads(options.decode('utf-8'), object_pairs_hook=unique_object,
                              parse_constant=reject_constant)
        if type(settings) is not dict or set(settings) != {'qubits', 'shots', 'seed'}:
            raise ValueError()
        validate_options(backend, settings['qubits'], settings['shots'], settings['seed'], 0, 0)
        prepared = prepare(program, settings['qubits'])
        with tempfile.TemporaryDirectory(prefix='qristal-local-') as directory:
            path = Path(directory) / 'canonical.qasm'
            path.write_bytes(prepared.canonical)
            command = [sys.executable, '/opt/qristal/runtime.py', '--qasm', str(path),
                       '--backend', backend, '--qubits', str(settings['qubits']),
                       '--shots', str(settings['shots']), '--seed', str(settings['seed'])]
            code, stdout, stderr = capture(command, timeout=60)
            if stderr:
                raise ValueError()
            result = validate_candidate(stdout, returncode=code, program=prepared.canonical,
                                        backend=backend, qubits=settings['qubits'], shots=settings['shots'])
        return LocalObservation(prepared.original_sha256, result.program_sha256,
                                hashlib.sha256(options).hexdigest(), result)
    except Exception:
        raise PipelineError('local_pipeline_rejected') from None
