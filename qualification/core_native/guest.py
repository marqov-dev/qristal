"""One disposable Core build; isolated stages, installed-only consumers and logs."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import zlib

ROOT=Path('/work')
LOGS=Path('/proof/core-logs')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while data:=stream.read(1024*1024):h.update(data)
    return h.hexdigest()


def emit(report):
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
    encoded=base64.b64encode(zlib.compress(raw,9)).decode()
    if len(encoded)>128*160:
        raw=json.dumps({'kind':'qb-core-native/v1','error':'report_bounds'}).encode()
        encoded=base64.b64encode(zlib.compress(raw)).decode()
    parts=[encoded[i:i+160] for i in range(0,len(encoded),160)]
    for _ in range(2):
        for n,part in enumerate(parts):print('QB_ADAPTER_CHUNK',hashlib.sha256(raw).hexdigest(),n,len(parts),part,flush=True)


def main():
    report={'kind':'qb-core-native/v1','native_passed':False,'stages':{}}
    LOGS.mkdir()
    deadline=time.monotonic()+max(1,min(3000,float(os.environ['CORE_DEADLINE'])-time.time()-330))
    owned=None
    def run(command,limit,name):
        logfile=LOGS/(name+'.log');start=time.monotonic()
        timed_out=False
        with logfile.open('wb') as log:
            try:
                seconds=min(limit,deadline-time.monotonic())
                if seconds<=0:raise subprocess.TimeoutExpired(command,0)
                code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=seconds).returncode
            except subprocess.TimeoutExpired:
                code=None;timed_out=True
        text=logfile.read_text(errors='replace')
        result={'index':len(report['stages']),'command':command,'exit':code,'timeout':timed_out,'seconds':time.monotonic()-start,
                'log_sha256':digest(logfile),'head':text[:400],'tail':text[-1200:]}
        report['stages'][name]=result
        return result
    try:
        manifest=ROOT/'inputs/material-manifest.json'
        report['materials_sha256']=digest(manifest)
        expected=json.loads((ROOT/'protocol.json').read_text())
        if report['materials_sha256']!=expected['materials_sha256'] or digest(ROOT/'guest.py')!=expected['guest_sha256']:
            raise ValueError('protocol identity')
        report['protocol_sha256']=digest(ROOT/'protocol.json')
        # Context contains only pinned base declaration and public apt package recipe.
        context=Path('/proof/builder');context.mkdir()
        for name in ('Dockerfile','install-toolchain.sh'):
            if digest(ROOT/name)!=expected['builder_files'][name]:raise ValueError('builder identity')
            shutil.copyfile(ROOT/name,context/name)
        if run(['docker','build','--iidfile','/proof/builder-id',str(context)],600,'builder')['exit']!=0:
            raise RuntimeError('builder failed')
        image=Path('/proof/builder-id').read_text().strip();report['builder_image']=image
        work=ROOT/'native-work';work.mkdir(mode=0o777);work.chmod(0o777)
        def container(command,limit,name,installed=False):
            nonlocal owned
            owned='qb-core-'+name
            cmd=['docker','run','--name',owned,'--network','none','--read-only','--cpus','2',
                 '--memory','4g','--memory-swap','4g','--pids-limit','256','--cap-drop','ALL',
                 '--security-opt','no-new-privileges','--user','65532:65532',
                 '--tmpfs','/tmp:rw,exec,size=512m','--workdir','/tmp']
            if installed:
                for item in ('install-core','install-xacc','python-core'):
                    cmd+=['--mount',f'type=bind,source={work/item},target=/work/{item},readonly']
                cmd+=['--mount',f'type=bind,source={ROOT}/inputs/consumer,target=/consumer,readonly',
                      '--mount',f'type=bind,source={work}/consumer-output,target=/consumer-output'+('' if name=='consumer-build' else ',readonly')]
            else:
                cmd+=['--mount',f'type=bind,source={ROOT}/inputs,target=/inputs,readonly',
                      '--mount',f'type=bind,source={work},target=/work']
            cmd+=['--entrypoint','/usr/bin/env',image,'-i','PATH=/work/python-core/bin:/usr/local/bin:/usr/bin:/bin',
                  'HOME=/tmp','OMP_NUM_THREADS=2','OPENBLAS_NUM_THREADS=2','PYTHONDONTWRITEBYTECODE=1',
                  'PYTHONNOUSERSITE=1','PYTHONPATH=/work/install-core/lib:/work/install-core/python-site']+command
            result=run(cmd,limit,name)
            removed=subprocess.run(['docker','rm','-f',owned],capture_output=True,timeout=30).returncode==0
            absent=subprocess.run(['docker','inspect',owned],capture_output=True,timeout=15).returncode!=0
            result['container_removed']=removed and absent;owned=None
            if result['exit']!=0 or not result['container_removed']:raise RuntimeError(name+' failed')
            return result
        container(['python3','/inputs/native/verify_materials.py','/inputs'],90,'verify-inputs')
        container(['sh','-c','c++ --version; cmake --version; python3 --version; cat /toolchain-packages.txt'],60,'inventory')
        container(['python3','/inputs/native/stage_work.py','stage'],120,'stage-inputs')
        # Replay the previously retained XACC consumer before Core changes its prefix.
        container(['/work/extracted-xacc/tree/consumer-output/acz','--installed'],60,'xacc-replay')
        for name,limit in [('antlr',120),('python',180),('configure',360)]:
            container(['sh','/inputs/native/stages.sh',name],limit,name)
        container(['python3','/inputs/native/stage_work.py','audit-core'],60,'source-audit')
        container(['python3','/inputs/tools/qualification/core_selection/check.py','/work/build-core/CMakeCache.txt'],60,'selection')
        container(['sh','/inputs/native/stages.sh','build'],1800,'build')
        container(['python3','/inputs/native/stage_work.py','audit-core'],60,'source-audit-built')
        container(['python3','/inputs/tools/qualification/core_selection/check.py','/work/build-core/CMakeCache.txt'],60,'selection-built')
        container(['sh','/inputs/native/stages.sh','install'],180,'install')
        container(['python3','/inputs/output/output.py','normalize','/work','/work/plugin-normalization.json'],60,'normalize-links')
        container(['python3','/inputs/tools/qualification/core_selection/after_install.py','/work'],60,'install-audit')
        (work/'consumer-output').mkdir(mode=0o777);(work/'consumer-output').chmod(0o777)
        container(['sh','-c','cmake -S /consumer -B /consumer-output -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/work/install-core;/work/install-xacc" -DXACC_ROOT=/work/install-xacc && cmake --build /consumer-output --parallel 2'],180,'consumer-build',True)
        container(['/consumer-output/core-installed'],60,'consumer-cpp',True)
        container(['/work/python-core/bin/python','/consumer/core.py'],60,'consumer-python',True)
        linkage=container(['sh','-c','ldd /consumer-output/core-installed; find /work/install-core/lib -name "*.so*" -type f -exec ldd {} \;'],60,'installed-linkage',True)
        # Full linkage log must be checked, not merely its clipped console tail.
        linkage_text=(LOGS/'installed-linkage.log').read_text()
        if 'not found' in linkage_text or '/work/build-core' in linkage_text or '/opt/qb' in linkage_text:
            raise ValueError('installed linkage')
        if 'PASS: installed Core C++ QPP identity and Bell' not in (LOGS/'consumer-cpp.log').read_text():raise ValueError('C++ result marker')
        if 'PASS: installed Core Python QPP identity and Bell' not in (LOGS/'consumer-python.log').read_text():raise ValueError('Python result marker')
        report['plugin_normalization']=json.loads((work/'plugin-normalization.json').read_text())
        report['retained_files']={prefix+'/'+p.relative_to(root).as_posix():digest(p) for prefix,root in {'antlr':work/'antlr/wheels','consumer':ROOT/'inputs/consumer','consumer-output':work/'consumer-output'}.items() for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
        report['native_passed']=True
    except Exception as error:
        report['error']=type(error).__name__+':'+str(error)
    finally:
        if owned:subprocess.run(['docker','rm','-f',owned],capture_output=True,timeout=30)
        try:
            spec=importlib.util.spec_from_file_location('core_output',ROOT/'inputs/output/output.py')
            output=importlib.util.module_from_spec(spec);spec.loader.exec_module(output)
            roots={'logs':LOGS}
            if report['native_passed']:
                roots.update({'install-core':work/'install-core','install-xacc':work/'install-xacc',
                              'antlr':work/'antlr/wheels','consumer':ROOT/'inputs/consumer','consumer-output':work/'consumer-output'})
            archive_path=Path('/proof/core-output.tar.gz')
            try:
                identity=output.pack(archive_path,report,roots)
            except Exception as error:
                # Keep diagnostic evidence if a successful installation cannot
                # satisfy the strict output policy. Never widen the root scope.
                report['native_passed']=False
                report['error']='output packaging failed:'+type(error).__name__
                archive_path=Path('/proof/core-failure.tar.gz')
                identity=output.pack(archive_path,report,{'logs':LOGS})
            code=subprocess.run(['curl','--config','/proof/output-put.conf','--silent','--fail','--max-time','300',
                                 '--upload-file',str(archive_path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=315).returncode
            if code:raise RuntimeError('artifact upload')
            report['output_artifact']=identity
        except Exception as error:
            report['output_artifact_error']=type(error).__name__
        Path('/proof/output-put.conf').unlink(missing_ok=True)
        emit(report)


if __name__=='__main__':main()
