"""Independent Fourier-matrix replay of saved complex vectors; no native compute."""
import cmath
import json
import math

MODES = ('basis', 'qft', 'iqft', 'qft-iqft', 'iqft-qft')


def reference(n, value, mode):
    size = 1 << n
    if mode in ('qft', 'iqft'):
        sign = 1 if mode == 'qft' else -1
        return [cmath.exp(sign*2j*math.pi*value*y/size)/math.sqrt(size) for y in range(size)]
    return [complex(y == value) for y in range(size)]


def verify(records):
    expected = {(n, value, mode) for n in range(1, 4) for value in range(1 << n) for mode in MODES}
    seen = set()
    maximum = {mode: 0.0 for mode in MODES}
    for record in records:
        if set(record) != {'qubits','input','mode','max_abs_error','norm_error','amplitudes'}:
            raise ValueError('case_fields')
        n, value, mode = record['qubits'], record['input'], record['mode']
        if type(n) is not int or type(value) is not int or type(mode) is not str:
            raise ValueError('case_identity')
        key = n, value, mode
        if key not in expected or key in seen:
            raise ValueError('case_identity')
        seen.add(key)
        pairs = record['amplitudes']
        if not isinstance(pairs,list) or len(pairs) != 1 << n:
            raise ValueError('wave_shape')
        wave = []
        for pair in pairs:
            if not isinstance(pair,list) or len(pair)!=2 or any(type(x) not in (float,int) or not math.isfinite(x) for x in pair):
                raise ValueError('wave_component')
            wave.append(complex(*pair))
        error = max(abs(a-b) for a,b in zip(wave, reference(n,value,mode)))
        norm_error = abs(sum(abs(a)**2 for a in wave)-1)
        tolerance = 1e-6 if mode in ('qft','iqft') else 1e-10
        if error > tolerance or norm_error > 1e-10:
            raise ValueError('fourier_reference_mismatch')
        for reported, actual in ((record['max_abs_error'],error), (record['norm_error'],norm_error)):
            if type(reported) not in (float,int) or not math.isfinite(reported) or abs(reported-actual)>1e-12:
                raise ValueError('error_metadata')
        maximum[mode] = max(maximum[mode],error)
    if seen != expected:
        raise ValueError('missing_cases')
    return {'cases':len(seen), 'max_abs_error_by_mode':maximum,
            'scope':'1-3 qubit QPP complex-state fixtures; not full Decoder qualification'}


def from_stdout(stdout):
    return [json.loads(line.removeprefix('QFT_CASE ')) for line in stdout.splitlines() if line.startswith('QFT_CASE ')]
