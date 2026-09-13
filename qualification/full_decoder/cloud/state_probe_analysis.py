"""Parse sampled sparse state without treating timeout or sampled maxima as completion."""
import json

def parse(output):
    calls=[]
    for line in output.splitlines():
        if not line.startswith('SPARSE_STATE '):continue
        row=json.loads(line.removeprefix('SPARSE_STATE '))
        event=row['event']
        if event not in ('begin','phase_begin','phase_end','sample','sample_begin','sample_end'):raise ValueError('event')
        for key in ('phase','nodes','elapsed_us','states','operations','h','rx','ry'):
            if type(row[key]) is not int or row[key]<0:raise ValueError('nonnegative_integer')
        if row['states']>2**24 or max(row['h'],row['rx'],row['ry'])>64:raise ValueError('state_bound')
        if event=='begin':
            if row['nodes'] or row['phase']:raise ValueError('begin_shape')
            calls.append([])
        if not calls:raise ValueError('missing_begin')
        current=calls[-1]
        if current:
            previous=current[-1]
            if any(row[k]<previous[k] for k in ('nodes','elapsed_us','phase')):raise ValueError('nonmonotonic')
            if previous['event']=='sample_end':raise ValueError('after_sampling')
        if event=='sample' and row['nodes']%8192:raise ValueError('sample_interval')
        if event=='sample_end' and (not current or current[-1]['event']!='sample_begin'):raise ValueError('sampling_pair')
        current.append(row)
    if not calls:raise ValueError('missing_observations')
    summaries=[]
    for rows in calls:
        phases=[]
        for p in sorted({r['phase'] for r in rows}):
            group=[r for r in rows if r['phase']==p]
            phases.append({'phase':p,'samples':len(group),'first':group[0],'last':group[-1],
              'sampled_max_stored_states':max(r['states'] for r in group),
              'sampled_max_queued_operations':max(r['operations'] for r in group)})
        summaries.append({'sampling_completed':rows[-1]['event']=='sample_end','observations':len(rows),'phases':phases})
    return summaries,calls


def backend_durations(output):
    import re
    durations=[];pending=None
    for event,stamp in re.findall(r'SEARCH_TRACE backend_execute_(begin|end) elapsed_ms=(\d+)',output):
        stamp=int(stamp)
        if event=='begin':
            if pending is not None:raise ValueError('overlapping_backend')
            pending=stamp
        else:
            if pending is None or stamp<pending:raise ValueError('backend_pair')
            durations.append(stamp-pending);pending=None
    return {'completed_call_ms':durations,'incomplete_call_started':pending is not None}
