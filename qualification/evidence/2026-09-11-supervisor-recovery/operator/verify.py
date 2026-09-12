import json,sys,time
from pathlib import Path
sys.path.insert(0,'/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/gpu_release')
from observer import atomic_json
from supervisor import Client
root=Path(__file__).resolve().parent
plan=json.loads((root/'plan.json').read_text())
ids=json.loads((root/'run/resources.json').read_text())
assert ids['cleanup_verified']
client=Client(plan['region'])
account=client('get-caller-identity',{},30)['Account']
assert account==plan['account']
instances=client('describe-instances',{'Filters':[{'Name':'client-token','Values':[plan['run']]}]},30)
observed=[{'id':i['InstanceId'],'state':i['State']['Name']} for r in instances['Reservations'] for i in r['Instances']]
assert observed==[{'id':ids['instance'],'state':'terminated'}]
volumes=client('describe-volumes',{'Filters':[{'Name':'volume-id','Values':ids['volumes']}]},30)['Volumes']
groups=client('describe-security-groups',{'Filters':[{'Name':'group-id','Values':[ids['group']]}]},30)['SecurityGroups']
assert not volumes and not groups
record={'observed_epoch':time.time(),'account':account,'region':plan['region'],
        'instances_matching_original_token':observed,'exact_volume_ids':ids['volumes'],
        'remaining_volumes':len(volumes),'security_group_id':ids['group'],'remaining_groups':len(groups)}
atomic_json(root/'verification.json',record)
print(json.dumps(record))
