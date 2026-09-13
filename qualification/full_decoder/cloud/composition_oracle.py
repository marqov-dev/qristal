"""Independent checks of the phase experiment's raw states and structure counts."""
import math


def verify_states(states):
    expected={(route, angle) for route in ('candidate','legacy') for angle in (.37,-.37,.9,-.9)}
    seen=set(); observed=[]
    for item in states:
        key=(item['route'],item['angle'])
        if key not in expected or key in seen: raise ValueError('case_inventory')
        seen.add(key)
        pairs=item['amplitudes']
        if len(pairs)!=8 or any(len(p)!=2 for p in pairs): raise ValueError('state_shape')
        wave=[complex(*p) for p in pairs]
        if not all(math.isfinite(z.real) and math.isfinite(z.imag) for z in wave): raise ValueError('nonfinite_state')
        norm=sum(abs(z)**2 for z in wave)
        if abs(norm-1)>1e-10: raise ValueError('state_norm')
        probability=sum(abs(wave[i])**2 for i in range(4,8))
        if not math.isfinite(item['outer_one_probability']) or abs(probability-item['outer_one_probability'])>1e-12:
            raise ValueError('probability_binding')
        if item['route']=='candidate' and probability>=1e-20: raise ValueError('candidate_interference')
        observed.append({'route':item['route'],'angle':item['angle'],'outer_one_probability':probability})
    if seen!=expected: raise ValueError('case_inventory')
    return {'candidate_cases':4,'legacy_observations':4,'observations':observed}


def verify_inventory(items):
    roots=[x for x in items if x['kind']=='preparation']
    inverses=[x for x in items if x['kind']=='legacy_inverse']
    children=[x for x in items if x['kind']=='child']
    if len(roots)!=1 or len(inverses)!=1 or not children or len(items)!=len(children)+2:
        raise ValueError('inventory_shape')
    if [x['index'] for x in children]!=list(range(len(children))): raise ValueError('child_indices')
    for item in items:
        for key in ('nodes','primitive_leaves','eligible_control_blocks','estimated_sparse_visits'):
            if type(item[key]) is not int or not 0<=item[key]<=1000000: raise ValueError('inventory_bound')
        names=item['composite_names']
        if any(type(v) is not int or v<1 for v in names.values()): raise ValueError('name_counts')
        if item['nodes']!=item['primitive_leaves']+sum(names.values()): raise ValueError('node_accounting')
        if item['estimated_sparse_visits']>item['nodes']: raise ValueError('estimate_bound')
    root=roots[0]; inverse=inverses[0]
    for key,extra in (('nodes',1),('primitive_leaves',0),('eligible_control_blocks',0)):
        if root[key]!=sum(x[key] for x in children)+extra: raise ValueError('child_accounting')
    return {'preparation':root,'legacy_inverse':inverse,'top_level_children':len(children),
            'largest_children':sorted(children,key=lambda x:x['nodes'],reverse=True)[:5],
            'estimates_are_not_measured_runtime':True,'construction_only':True}
