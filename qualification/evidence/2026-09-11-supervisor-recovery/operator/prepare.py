import json, os, subprocess, sys, uuid, tempfile, re
from pathlib import Path
sys.path.insert(0, '/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/gpu_release')
from observer import atomic_json
from supervisor import Supervisor
root=Path(__file__).resolve().parent
run=json.loads((root/'intent.json').read_text())['run'] if (root/'intent.json').exists() else 'qb-proof-'+uuid.uuid4().hex
def aws(operation, params):
    with tempfile.NamedTemporaryFile(mode='w+') as request:
        json.dump(params,request)
        request.flush()
        p=subprocess.run(['aws','ec2',operation,'--region','us-east-1','--output','json',
                          '--cli-input-json','file://'+request.name],
                         capture_output=True,text=True,timeout=45)
    if p.returncode:
        raise RuntimeError('preparation_failed_'+operation+'_'+str(re.findall(r'An error occurred \(([A-Za-z0-9.]+)\)',p.stderr)))
    return json.loads(p.stdout)
atomic_json(root/'intent.json', {
    'run': run, 'purpose': 'native supervisor interruption/recovery, not simulator qualification',
    'source': '80e6772', 'instance_type':'g5.xlarge', 'maximum_instances':1,
    'observation_seconds':600, 'cleanup_seconds':300, 'guest_shutdown_minutes':8,
    'network_ingress':False, 'network_egress':False, 'workload_credentials':False,
})
group=aws('create-security-group', {
    'GroupName':run,'Description':'Disposable QB supervisor recovery probe',
    'VpcId':'vpc-0c8ff9e3276495a4c',
    'TagSpecifications':[{'ResourceType':'security-group','Tags':[{'Key':'QBProofRun','Value':run}]}]
})['GroupId']
atomic_json(root/'group.json',{'group':group,'run':run})
groups=aws('describe-security-groups',{'GroupIds':[group]})['SecurityGroups']
if groups[0].get('IpPermissionsEgress'):
    aws('revoke-security-group-egress',{'GroupId':group,'IpPermissions':groups[0]['IpPermissionsEgress']})
plan={'account':'090208085542','region':'us-east-1','run':run,
      'image':'ami-0eb7d782cce2fe526','subnet':'subnet-01fb5ff873d16c141',
      'group':group,'vpc':'vpc-0c8ff9e3276495a4c','instance_type':'g5.xlarge','root_gib':200}
atomic_json(root/'plan.json',plan)
Supervisor.initialize(root/'run',plan,(root/'bootstrap.sh').read_bytes(),
                      seconds=600,cleanup_seconds=300)
print(json.dumps({'run':run,'group':group,'prepared':True}))
