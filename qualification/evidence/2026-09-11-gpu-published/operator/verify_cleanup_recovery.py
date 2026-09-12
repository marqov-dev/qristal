"""Read-only cleanup audit after observer connectivity loss; preserve limitations."""
import datetime
import json
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parent
instance='i-0df84e33cffc898ce'; group='sg-0f740f36e98ddaacc'

def aws(*args):
 p=subprocess.run(['aws','ec2',*args,'--region','us-east-1','--output','json','--cli-connect-timeout','10','--cli-read-timeout','15'],capture_output=True,text=True,timeout=45)
 if p.returncode: raise SystemExit('cleanup_audit_api_failed: '+args[0])
 return json.loads(p.stdout)

instances=aws('describe-instances','--filters','Name=instance-id,Values='+instance)['Reservations']
if instances: raise SystemExit('instance_still_present')
groups=aws('describe-security-groups','--filters','Name=group-id,Values='+group)['SecurityGroups']
if groups: raise SystemExit('security_group_still_present')
# This intentionally scans the full region, regardless of size, state or attachment.
volumes=aws('describe-volumes','--query','Volumes[].{id:VolumeId,created:CreateTime,zone:AvailabilityZone}')
start=datetime.datetime.fromisoformat('2026-09-11T10:19:00+00:00')
end=datetime.datetime.fromisoformat('2026-09-11T10:23:00+00:00')
matches=[v for v in volumes if start<=datetime.datetime.fromisoformat(v['created'].replace('Z','+00:00'))<=end]
if matches: raise SystemExit('volume_in_launch_window_requires_identification')
record={'instance_absent':True,'volumes_absent':True,'security_group_deleted':True,'security_group_absent':True,'instance_id':instance,'volume_ids':[],'security_group_id':group,'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'volume_verification':{'method':'full-region creation-window scan; exact root-volume ID was not retained by the interrupted observer','region':'us-east-1','from_inclusive':start.isoformat(),'to_inclusive':end.isoformat(),'matching_volumes':matches,'launch_event_time':'2026-09-11T10:20:53Z'},'limitation':'No terminated-state response or exact root-volume-ID absence response was retained; instance absence and the full launch-window volume scan were observed independently.'}
(root/'cleanup.json').write_text(json.dumps(record,indent=2)+'\n')
print('INSTANCE_AND_SECURITY_GROUP_ABSENT; NO_EBS_VOLUME_IN_LAUNCH_WINDOW')
