"""One disposable GPU proof. No IAM role, SSH key, inbound rule or public service."""
from pathlib import Path
import base64,json,subprocess,time,uuid,sys
sys.path.insert(0,"/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/gpu_package")
from console import recover
def decode(text):
 return recover(text)[0]
root=Path(__file__).resolve().parent
run='codex-qb-gpu-'+uuid.uuid4().hex[:10]

def aws(*args):
 p=subprocess.run(['aws',*args,'--region','us-east-1','--output','json'],capture_output=True,text=True,timeout=45)
 if p.returncode: raise RuntimeError(p.stderr[-1200:])
 return json.loads(p.stdout or '{}')

def save(name,data):
 (root/name).write_text(json.dumps(data,indent=2)+'\n')

sg=None;instance=None;volumes=[]
try:
 sg=aws('ec2','create-security-group','--group-name',run,'--description','Disposable QB GPU proof; no inbound access',
        '--vpc-id','vpc-0c8ff9e3276495a4c')['GroupId']
 save('resources.json',{'group':sg,'run':run})
 aws('ec2','revoke-security-group-egress','--group-id',sg,'--ip-permissions',json.dumps([{'IpProtocol':'-1','IpRanges':[{'CidrIp':'0.0.0.0/0'}]}]))
 aws('ec2','authorize-security-group-egress','--group-id',sg,'--ip-permissions',json.dumps([{'IpProtocol':'tcp','FromPort':443,'ToPort':443,'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}]))
 launched=aws('ec2','run-instances','--image-id','ami-0eb7d782cce2fe526','--instance-type','g5.xlarge','--count','1',
 '--subnet-id','subnet-01fb5ff873d16c141','--security-group-ids',sg,'--associate-public-ip-address',
 '--metadata-options','HttpTokens=required,HttpPutResponseHopLimit=1','--instance-initiated-shutdown-behavior','terminate',
 '--block-device-mappings',json.dumps([{'DeviceName':'/dev/sda1','Ebs':{'VolumeSize':200,'VolumeType':'gp3','Encrypted':True,'DeleteOnTermination':True}}]),
 '--tag-specifications',json.dumps([{'ResourceType':'instance','Tags':[{'Key':'Name','Value':run},{'Key':'Project','Value':'codex-qb-proof'}]}]),
 '--client-token',run,'--user-data','file://'+str(root/'userdata.sh'))
 instance=launched['Instances'][0]['InstanceId']
 volumes=[m['Ebs']['VolumeId'] for m in launched['Instances'][0].get('BlockDeviceMappings',[]) if 'Ebs' in m]
 save('resources.json',{'group':sg,'instance':instance,'run':run})
 print('LAUNCHED '+instance,flush=True)
 deadline=time.monotonic()+3600
 laststate=None;lastmarker=None
 while time.monotonic()<deadline:
  info=aws('ec2','describe-instances','--instance-ids',instance)['Reservations'][0]['Instances'][0]
  volumes=[m['Ebs']['VolumeId'] for m in info.get('BlockDeviceMappings',[]) if 'Ebs' in m] or volumes
  state=info['State']['Name']
  if state!=laststate: print('STATE '+state,flush=True);laststate=state
  console=aws('ec2','get-console-output','--instance-id',instance,'--latest')
  output=console.get('Output','')
  if output: (root/'console.log').write_text(output)
  try: report=decode(output)
  except Exception: report=None
  if report is not None:
   save('result.json',report)
   recovered, complete, truncated = recover(output)
   (root/'console-observed.txt').write_text(output)
   (root/'console-chunks.txt').write_text(complete)
   save('console-recovery.json',{'discarded_truncated_nonfinal_fragments':truncated})
   if lastmarker!='passed':print('GPU_ADAPTER_PASSED',flush=True);lastmarker='passed'
  if state=='terminated':break
  time.sleep(20)
finally:
 if instance:
  aws('ec2','terminate-instances','--instance-ids',instance)
  for attempt in range(90):
   state=aws('ec2','describe-instances','--instance-ids',instance)['Reservations'][0]['Instances'][0]['State']['Name']
   if state=='terminated':break
   time.sleep(5)
  else:raise RuntimeError('termination_not_verified')
  if not volumes: raise RuntimeError('volume_identity_not_observed')
  for attempt in range(12):
   found=aws('ec2','describe-volumes','--filters','Name=volume-id,Values='+','.join(volumes))['Volumes'] if volumes else []
   if not found:break
   time.sleep(5)
  if found:raise RuntimeError('volume_deletion_not_verified')
 if sg:
  for attempt in range(12):
   try:aws('ec2','delete-security-group','--group-id',sg);break
   except RuntimeError:
    if attempt==11:raise
    time.sleep(5)
 save('cleanup.json',{'instance_terminated':bool(instance),'volumes_absent':True,'security_group_deleted':bool(sg),'instance_id':instance,'volume_ids':volumes,'security_group_id':sg})
 print('CLEANUP_VERIFIED',flush=True)
if not (root/'result.json').exists():raise RuntimeError('GPU result not received; inspect retained console')
