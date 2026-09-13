"""Independent dense controlled-inverse reference for retained native vectors."""
import cmath
import math

LAYOUTS=((3,(0,),1),(4,(3,0),2))
OPS=(('X',0),('Y',0),('Z',0),('H',0),('Rx',.37),('Rx',-.37),('Ry',.37),('Ry',-.37),('Rz',.37),('Rz',-.37))
MODES=('inverse','populated','roundtrip','clone','disabled','mapped','fallback','nested')

def expected(layout,operation):
    n,controls,target=LAYOUTS[layout]
    name,angle=OPS[operation];angle=-angle
    state=[cmath.exp(1j*sum((1 if (basis>>bit)&1 else -1)*.13*(bit+1)/2 for bit in range(n)))/math.sqrt(2**n) for basis in range(2**n)]
    c,s=math.cos(angle/2),math.sin(angle/2)
    matrix={'X':((0,1),(1,0)),'Y':((0,-1j),(1j,0)),
            'Z':((1,0),(0,-1)),'H':((2**-.5,2**-.5),(2**-.5,-2**-.5)),
            'Rx':((c,-1j*s),(-1j*s,c)),'Ry':((c,-s),(s,c)),
            'Rz':((cmath.exp(-.5j*angle),0),(0,cmath.exp(.5j*angle)))}[name]
    result=[0j]*len(state)
    for source,value in enumerate(state):
        if not all((source>>control)&1 for control in controls):result[source]+=value;continue
        col=(source>>target)&1
        for row in (0,1):
            destination=(source&~(1<<target))|(row<<target)
            result[destination]+=matrix[row][col]*value
    return result

def verify(records):
    inventory={(l,o,m) for l in range(2) for o in range(10) for m in MODES}
    seen=set();maximum=0.;vectors=0;legacy=[]
    for record in records:
        key=(record['layout'],record['operation'],record['mode'])
        if key not in inventory or key in seen:raise ValueError('case_inventory')
        seen.add(key)
        error=record['error']
        if isinstance(error,bool) or not math.isfinite(error) or error<0 or (key[2]!='fallback' and error>=1e-10):raise ValueError('native_error_bound')
        if key[2] in ('inverse','fallback'):
            wanted=expected(key[0],key[1]);raw=record['amplitudes']
            if len(raw)!=len(wanted):raise ValueError('state_shape')
            actual=[]
            for pair in raw:
                if len(pair)!=2 or any(isinstance(x,bool) or not math.isfinite(x) for x in pair):raise ValueError('nonfinite_state')
                actual.append(complex(*pair))
            difference=max(abs(a-b) for a,b in zip(actual,wanted))
            if key[2]=='fallback':
                if abs(difference-error)>1e-10:raise ValueError('legacy_error_binding')
                pivot=max(range(len(wanted)),key=lambda i:abs(wanted[i]))
                phase=actual[pivot]/wanted[pivot]
                aligned=max(abs(a-phase*b) for a,b in zip(actual,wanted))
                legacy.append(dict(layout=key[0],operation=key[1],error=difference,
                                   matches_exact_oracle=difference<1e-10,
                                   diagnostic_phase_angle=cmath.phase(phase),
                                   diagnostic_phase_aligned_error=aligned))
            else:
                if difference>=1e-10:raise ValueError('independent_phase_mismatch')
                maximum=max(maximum,difference)
            vectors+=1
        elif 'amplitudes' in record:raise ValueError('unexpected_vector')
    if seen!=inventory:raise ValueError('case_inventory')
    return dict(candidate_matrix_cases=140,independently_replayed_vectors=vectors,candidate_vectors=20,legacy_vectors=20,max_candidate_complex_error=maximum,legacy_observations=legacy,legacy_mismatches=sum(not row["matches_exact_oracle"] for row in legacy))

def sparse_probabilities(layout,operation):
    state=expected(layout,operation);target=LAYOUTS[layout][2]
    result=[]
    for basis in range(len(state)):
        zero=basis&~(1<<target);one=zero|(1<<target)
        value=(state[zero]+(-1 if (basis>>target)&1 else 1)*state[one])/math.sqrt(2)
        result.append(abs(value)**2)
    return result

def verify_sparse(records):
    seen=set();maximum=0
    for record in records:
        key=(record['layout'],record['operation'])
        if key in seen or key not in {(l,o) for l in range(2) for o in range(10)}:raise ValueError('sparse_inventory')
        seen.add(key);counts=record['counts'];wanted=sparse_probabilities(*key)
        if len(counts)!=len(wanted) or any(type(c) is not int or c<0 for c in counts) or sum(counts)!=16384:raise ValueError('sparse_counts')
        residual=max(abs(c/16384-p) for c,p in zip(counts,wanted))
        if residual>=.025:raise ValueError('sparse_phase_mismatch')
        maximum=max(maximum,residual)
    if len(seen)!=20:raise ValueError('sparse_inventory')
    return dict(cases=20,shots=16384,max_probability_residual=maximum,tolerance=.025)
