import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/gpu_release')
from observer import atomic_json
root=Path(__file__).resolve().parent
source=Path('/private/tmp/marqov-qristal-followup-20260909/qristal/qualification/gpu_release/supervisor.py')
atomic_json(root/'source.json',{'revision':'80e6772','supervisor_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
with (root/'controller.log').open('w') as log:
    child=subprocess.Popen([sys.executable,str(source),'run','--directory',str(root/'run'),
                            '--userdata',str(root/'bootstrap.sh')],stdout=log,stderr=log)
    end=time.monotonic()+120
    while child.poll() is None and time.monotonic()<end:
        state=json.loads((root/'run/supervisor.json').read_text())
        if state['phase']=='observing':
            ids=json.loads((root/'run/resources.json').read_text())
            if ids['instance'] and ids['volumes']:
                os.kill(child.pid,signal.SIGKILL)
                code=child.wait(timeout=10)
                atomic_json(root/'interruption.json',{
                    'mechanism':'SIGKILL of owned local supervisor after durable launch/volume IDs',
                    'exit_code':code,'observed_epoch':time.time(),'resources_at_interruption':ids,
                    'original_observe_until':state['observe_until'],
                    'original_cleanup_until':state['cleanup_until'],
                })
                print(json.dumps({'interrupted':True,'exit_code':code,'instance':ids['instance'],
                                  'volume_ids':ids['volumes']}))
                break
        time.sleep(.2)
    else:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        raise RuntimeError('interruption_checkpoint_not_reached; inspect sanitized controller log and clean up')
