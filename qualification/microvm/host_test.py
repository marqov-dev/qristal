import hashlib,json,os,selectors,shutil,socket,subprocess,time,uuid,signal
from pathlib import Path
ROOT=Path('/opt/qb-proof');BASE=Path('/srv/jailer/firecracker');BASE.mkdir(parents=True,exist_ok=True)
PROGRAM=b'OPENQASM 2.0; include "qelib1.inc"; qreg r[2]; creg b[2]; x r[0]; measure r -> b;'
OPTIONS=b'{"qubits":2,"shots":17,"seed":42}'
Path('/qb-host-canary').write_text('SYNTHETIC-QB-CANARY-DO-NOT-COPY')
Path('/run/qb-management.sock').unlink(missing_ok=True)
management=socket.socket(socket.AF_UNIX);management.bind('/run/qb-management.sock')
report={'synthetic_data_only':True,'guest_credentials':False,'runs':[],'supervisor_epoch':uuid.uuid4().hex}
def run(mode,preparation=None):
 ident='qb-'+uuid.uuid4().hex[:12];operation=uuid.uuid4().hex;generation=uuid.uuid4().hex
 jail=BASE/ident/'root';jail.mkdir(parents=True)
 inp=ROOT/('input-'+ident);inp.mkdir()
 (inp/'mode').write_text(mode);(inp/'program.qasm').write_bytes(PROGRAM);(inp/'options.json').write_bytes(OPTIONS)
 if preparation:(inp/'preparation.json').write_text(json.dumps(preparation))
 subprocess.run(['truncate','-s','8M',str(jail/'input.ext4')],check=True)
 subprocess.run(['mkfs.ext4','-q','-F','-d',str(inp),str(jail/'input.ext4')],check=True)
 shutil.copyfile(ROOT/'rootfs.ext4',jail/'rootfs.ext4');shutil.copyfile(ROOT/'vmlinux-6.1.155',jail/'vmlinux')
 config={'boot-source':{'kernel_image_path':'/vmlinux','boot_args':'console=ttyS0 reboot=k panic=1 pci=off root=/dev/vda ro init=/qb-init.py quiet loglevel=0'},'drives':[{'drive_id':'root','path_on_host':'/rootfs.ext4','is_root_device':True,'is_read_only':True},{'drive_id':'input','path_on_host':'/input.ext4','is_root_device':False,'is_read_only':True}],'machine-config':{'vcpu_count':2,'mem_size_mib':4096,'smt':False}}
 (jail/'config.json').write_text(json.dumps(config))
 for path in jail.iterdir():os.chown(path,1234,1234)
 os.chown(jail,1234,1234)
 command=['/usr/local/bin/jailer','--id',ident,'--exec-file','/usr/local/bin/firecracker','--uid','1234','--gid','1234','--chroot-base-dir','/srv/jailer','--cgroup-version','2','--cgroup','cpu.max=200000 100000','--cgroup','memory.max=5368709120','--cgroup','pids.max=256','--','--config-file','/config.json','--no-api']
 start=time.monotonic();proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 output=bytearray();reason=None;ready=False
 try:
  with selectors.DefaultSelector() as select:
   os.set_blocking(proc.stdout.fileno(),False);select.register(proc.stdout,selectors.EVENT_READ)
   while select.get_map():
    if time.monotonic()-start>90:reason='deadline';break
    for key,_ in select.select(.5):
     data=os.read(key.fileobj.fileno(),4096)
     if not data:select.unregister(key.fileobj);break
     output.extend(data)
     if b'QB_INIT_FAILED=' in output:reason='bootstrap_failed';break
     if b'QB_EXIT=0' in output:reason='guest_completed';break
     if len(output)>131073:reason='output_limit';break
     if mode=='killed' and b'QB_WAITING' in output:ready=True;reason='requested_kill';break
    if reason:break
 finally:
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGKILL)
  code=proc.wait(timeout=10);proc.stdout.close()
 console=bytes(output);(ROOT/(ident+'.console')).write_bytes(console)
 try:os.kill(proc.pid,0);stopped=False
 except ProcessLookupError:stopped=True
 entry={'mode':mode,'guest_id':ident,'launch_operation':operation,'guest_generation':generation,'supervisor_epoch':report['supervisor_epoch'],'pid':proc.pid,'exit':code,'stop_observed':stopped,'reason':reason,'seconds':time.monotonic()-start,'console_bytes':len(console),'config_sha256':hashlib.sha256((jail/'config.json').read_bytes()).hexdigest()}
 report['runs'].append(entry);(ROOT/'report.json').write_text(json.dumps(report,indent=2))
 assert stopped
 if mode=='overflow':assert reason=='output_limit',console[-2500:];return None
 if mode=='killed':assert ready and reason=='requested_kill',console[-2500:];return None
 assert reason == "guest_completed" and code in (0,-9),console[-3500:]
 lines=console.decode(errors='replace').splitlines()
 assert 'QB_EXIT=0' in lines,lines[-15:]
 rows=[json.loads(line[len('QB_RESULT='):]) for line in lines if line.startswith('QB_RESULT=')]
 assert len(rows)==1
 assert any(line.startswith('QB_ISOLATION=') for line in lines)
 return rows[0]
try:
 preparation=run('prepare')
 run('validate',preparation)
 result=run('simulate',preparation)
 assert result['original_sha256']==hashlib.sha256(PROGRAM).hexdigest()
 assert result['options_sha256']==hashlib.sha256(OPTIONS).hexdigest()
 # Stale supervisor/generation tuple cannot be mistaken for the observed launch.
 first=report['runs'][0]
 expected=(first['supervisor_epoch'],first['launch_operation'],first['guest_generation'])
 assert ('stale',expected[1],expected[2])!=expected
 report['stale_identity_comparison']='synthetic tuple rejection only; no hosted writer'
 run('killed');run('overflow')
 report['passed']=True
finally:
 (ROOT/'report.json').write_text(json.dumps(report,indent=2))
 management.close()
print(json.dumps(report,indent=2))
