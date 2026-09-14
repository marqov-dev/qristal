import importlib.util,json,uuid
from pathlib import Path
root=Path('/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/core_package')
spec=importlib.util.spec_from_file_location('probe',root/'local_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
name='qpp-elf-audit-'+uuid.uuid4().hex[:16]
image='sha256:8d8a81d995325ae9c452dca2698442b02c735cc6eae9d98ea78a38532a5a8266'
cmd=['docker','run','--rm','--name',name,'--platform','linux/amd64','--network','none','--read-only','--cpus','2','--memory','4g','--memory-swap','4g','--pids-limit','256','--cap-drop','ALL','--security-opt','no-new-privileges','--user','65532:65532','--tmpfs','/tmp:rw,exec,size=512m','--mount','type=bind,source='+str(root/'image_audit_guest.py')+',target=/audit.py,readonly','--entrypoint','/work/python-core/bin/python',image,'/audit.py']
result={'command':cmd,'image_id':image,'passed':False,'native_amd64_hardware':False}
try:
 code,out,err=probe.bounded.capture(cmd,timeout=300,stdout_limit=8*1024*1024,stderr_limit=65536)
 result.update(exit_code=code,stderr=err.decode())
 lines=out.decode().splitlines();reports=[x[len('QPP_IMAGE_AUDIT '):] for x in lines if x.startswith('QPP_IMAGE_AUDIT ')]
 if len(reports)!=1:raise ValueError('audit report count')
 result['audit']=json.loads(reports[0]);result['passed']=code==0 and result['audit']['passed']
except Exception as e:result['error']=type(e).__name__
finally:
 try:
  rm=probe.bounded.capture(['docker','rm','-f',name],timeout=15,stdout_limit=1024,stderr_limit=2048)
  code,out,err=probe.bounded.capture(['docker','container','inspect','--format','{{.Id}}',name],timeout=15,stdout_limit=1024,stderr_limit=2048)
  absent=probe.absence(code,out,err,name)
  result['cleanup']={'remove_exit_code':rm[0],'absence_verified':absent,'inspect_exit_code':code,'stdout':out.decode(),'stderr':err.decode()};result['passed'] &= absent
 except Exception as e:result['cleanup']={'absence_verified':False,'error':type(e).__name__};result['passed']=False
Path('/private/tmp/qpp-image-audit-result-20260914.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':result['passed'],'elf_files':len(result.get('audit',{}).get('elf_files',[]))}))
