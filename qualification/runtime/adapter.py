"""Single-process workload-local CPU adapter; never a hosted authority boundary."""
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
import stat

MAX_PROGRAM_BYTES = 65536
MAX_RESULT_BYTES = 131072


class SampleError(ValueError):
    """A bounded public diagnostic, without backend exception or input contents."""


def require(ok, code):
    if not ok:
        raise SampleError(code)


def read_program(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as stream:
            require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), 'program_file')
            data = stream.read(MAX_PROGRAM_BYTES + 1)
        require(0 < len(data) <= MAX_PROGRAM_BYTES, 'program_size')
        return data
    except SampleError:
        raise
    except (OSError, TypeError, ValueError):
        raise SampleError('program_file') from None


def validate_program(data, qubits):
    require(type(data) is bytes and 0 < len(data) <= MAX_PROGRAM_BYTES, 'program_size')
    try:
        source = data.decode('utf-8')
    except UnicodeError:
        raise SampleError('program_utf8') from None
    # Preserve strings while removing comments so comments cannot spoof includes
    # or declarations. Full circuit parsing still runs only in the isolated engine.
    tokens = re.compile(r'("(?:[^"\\]|\\.)*")|//[^\r\n]*|/\*[\s\S]*?\*/')
    source = tokens.sub(lambda m: m.group(1) or ' ', source)
    require('/*' not in source and '*/' not in source, 'program_comment')
    require(not re.search(r'[^\t\n\r\x20-\x7e]', source), 'program_syntax')
    require(bool(re.match(r'\s*OPENQASM\s+2\.0\s*;', source)), 'program_version')
    require(len(re.findall(r'\bOPENQASM\b', source)) == 1, 'program_version')
    includes = list(re.finditer(r'\binclude\s+"qelib1\.inc"\s*;', source))
    require(len(includes) == 1 and len(re.findall(r'\binclude\b', source)) == 1, 'program_include')
    remainder = source[:includes[0].start()] + source[includes[0].end():]
    require('"' not in remainder, 'program_include')
    registers = re.findall(r'\bqreg\s+[A-Za-z_][A-Za-z0-9_]*\s*\[\s*(\d+)\s*\]\s*;', source)
    require(registers == [str(qubits)] and len(re.findall(r'\bqreg\b', source)) == 1, 'program_register')
    return source


def validate_options(backend, qubits, shots, seed, p10, p01):
    require(type(backend) is str and backend in ('qpp', 'aer'), 'backend')
    for value, low, high, code in [(qubits, 1, 12, 'qubits'), (shots, 1, 16384, 'shots'), (seed, 0, 2**31 - 1, 'seed')]:
        require(type(value) is int and low <= value <= high, code)
    for value in (p10, p01):
        require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, 'noise')
    require(backend == 'aer' or (p10 == 0 and p01 == 0), 'noise_backend')


def encode_result(data, backend, qubits, shots, raw):
    counts = {}
    try:
        for key in raw:
            bits = list(key)
            require(len(bits) == qubits and all(type(bit) is bool for bit in bits), 'result_bits')
            label = ''.join('1' if bit else '0' for bit in bits)
            count = raw[key]
            require(type(count) is int and 0 < count <= shots and label not in counts, 'result_counts')
            counts[label] = count
        require(sum(counts.values()) == shots, 'result_shots')
    except SampleError:
        raise
    except Exception:
        raise SampleError('result_counts') from None
    result = {'interface': 'local-qristal-sample/experimental', 'program_sha256': hashlib.sha256(data).hexdigest(),
              'backend': backend, 'shots': shots, 'bit_order': 'qubit_0_first', 'counts': counts}
    payload = json.dumps(result, sort_keys=True).encode('utf-8')
    require(len(payload) <= MAX_RESULT_BYTES, 'result_size')
    return payload


@contextmanager
def quiet_native_engine():
    # Fresh single-process CLI only: suppress C++ diagnostics as well as Python
    # output. A native abort/exit cannot become a valid JSON result by accident.
    saved = [os.dup(1), os.dup(2)]
    try:
        with open(os.devnull, 'wb') as sink:
            os.dup2(sink.fileno(), 1)
            os.dup2(sink.fileno(), 2)
            yield
    finally:
        for target, fd in zip((1, 2), saved):
            os.dup2(fd, target)
            os.close(fd)


def sample(data, *, backend='qpp', qubits=2, shots=4096, seed=42, p10=0.0, p01=0.0):
    validate_options(backend, qubits, shots, seed, p10, p01)
    source = validate_program(data, qubits)
    try:
        with quiet_native_engine():
            import qristal.core as q
            s = q.session()
            s.acc = backend; s.qn = qubits; s.sn = shots; s.seed = seed
            s.noplacement = True; s.nooptimise = True; s.aer_omp_threads = 2
            s.remote_backend_database_path = '/opt/qristal/empty-backends.yaml'
            s.instring = source
            s.noise = bool(p10 or p01)
            if p10 or p01:
                nm = q.NoiseModel(); nm.name = 'public_readout_demo'
                error = q.ReadoutError(); error.p_10 = p10; error.p_01 = p01
                nm.set_qubit_readout_error(0, error); s.noise_model = nm
            s.run()
            payload = encode_result(data, backend, qubits, shots, s.results)
        return payload
    except SampleError:
        raise
    except Exception:
        raise SampleError('engine_failed') from None
