#!/usr/bin/python3
import ctypes,os,subprocess,sys
try:
 for args in [['mount','-t','devtmpfs','devtmpfs','/dev'],['mount','-t','proc','proc','/proc'],['mount','-t','sysfs','sysfs','/sys'],['mount','-t','tmpfs','-o','size=128m,mode=1777','tmpfs','/tmp'],['mount','-o','ro','/dev/vdb','/inputs']]:
  if args[-1] == "/dev" and os.path.ismount("/dev"):continue
  subprocess.run(args,check=True)
 def drop():
  os.setgroups([]);os.setgid(65532);os.setuid(65532)
 env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin','HOME':'/tmp','TMPDIR':'/tmp','PYTHONPATH':'/work/install-core/lib:/runtime/python-core:/work/install-integrations','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','PYTHONUNBUFFERED':'1'}
 result=subprocess.run(['/usr/bin/python3','-B','/guest_workload.py'],env=env,preexec_fn=drop,timeout=120)
 print('QB_EXIT='+str(result.returncode),flush=True)
except Exception as e:
 print('QB_INIT_FAILED='+type(e).__name__,flush=True)
finally:
 os.sync()
 ctypes.CDLL(None).reboot(0x4321FEDC)
 while True:pass
