"""Independent mathematical replay of the predeclared MCZ fixture inventory."""
import cmath
import math

LAYOUTS = ((2,(0,),1),(3,(1,2),0),(4,(0,1,3),2),
           (5,(0,1,2,3),4),(5,(4,0),2),(5,(0,4),2))
MODES = ('direct','clone','inverse','pair','fallback','disabled','mapped')
TOLERANCE = 1e-10


def wave(layout, mode):
    n, controls, target = LAYOUTS[layout]
    if mode == 'mapped':
        controls = tuple(n-1-bit for bit in controls)
        target = n-1-target
    result = []
    for basis in range(2**n):
        value = 1+0j
        for bit in range(n):
            angle = 0.13*(bit+1)/2
            value *= cmath.exp(1j*angle*(1 if basis & (1<<bit) else -1))/math.sqrt(2)
        mask = sum(1<<bit for bit in (*controls,target))
        if mode not in ('pair','disabled') and basis & mask == mask:
            value *= -1
        result.append(value)
    return n, controls, target, result


def verify_states(records):
    expected = {(layout,mode) for layout in range(len(LAYOUTS)) for mode in MODES}
    seen = set()
    maximum = 0
    for record in records:
        key = (record['layout'],record['mode'])
        if key not in expected or key in seen:
            raise ValueError('state_inventory')
        seen.add(key)
        n, controls, target, reference = wave(*key)
        if (record['qubits'],tuple(record['controls']),record['target']) != (n,controls,target):
            raise ValueError('state_layout')
        values = [complex(*value) for value in record['amplitudes']]
        if len(values) != len(reference) or not all(math.isfinite(v.real) and math.isfinite(v.imag) for v in values):
            raise ValueError('state_shape_finite')
        error = max(abs(a-b) for a,b in zip(values,reference))
        if error > TOLERANCE or abs(sum(abs(v)**2 for v in values)-1) > TOLERANCE:
            raise ValueError('state_phase_or_norm')
        maximum = max(maximum,error)
    if seen != expected:
        raise ValueError('state_inventory')
    return dict(cases=len(seen),maximum_complex_error=maximum)


def sparse_inventory():
    expected = {}
    for k in (1,2,3,4,18):
        patterns = ((2**k-1,2**k-2) if k==18 else range(2**k))
        for pattern in patterns:
            for mode in ('direct','clone','inverse','pair','fallback'):
                if k==18 and mode=='fallback':
                    continue
                bits = ''.join(str((pattern>>bit)&1) for bit in range(k))
                bits += str(int(pattern==2**k-1 and mode!='pair'))
                expected[(k,pattern,mode)] = {bits:64}
    return expected


def verify_sparse(records):
    expected = sparse_inventory()
    seen = set()
    for record in records:
        key = (record['controls'],record['pattern'],record['mode'])
        if key not in expected or key in seen:
            raise ValueError('sparse_inventory')
        seen.add(key)
        if record['counts'] != expected[key]:
            raise ValueError('sparse_interference')
    if seen != set(expected):
        raise ValueError('sparse_inventory')
    return dict(cases=len(seen),shots_per_execution=64,repetitions_per_case=2)
