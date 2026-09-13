"""Classify a completed Core report after independent output-archive verification."""
import hashlib
import json
from pathlib import Path
import re
import tarfile

STAGES=('builder','verify-inputs','inventory','stage-inputs','xacc-replay','antlr','python',
        'configure','source-audit','selection','build','source-audit-built','selection-built',
        'install','normalize-links','install-audit','consumer-build','consumer-cpp','consumer-python','installed-linkage')
INSTALLED=set(STAGES[-4:])
COMMANDS={
 'verify-inputs':['python3','/inputs/native/verify_materials.py','/inputs'],
 'inventory':['sh','-c','c++ --version; cmake --version; python3 --version; cat /toolchain-packages.txt'],
 'stage-inputs':['python3','/inputs/native/stage_work.py','stage'],
 'xacc-replay':['/work/extracted-xacc/tree/consumer-output/acz','--installed'],
 'source-audit':['python3','/inputs/native/stage_work.py','audit-core'],
 'source-audit-built':['python3','/inputs/native/stage_work.py','audit-core'],
 'selection':['python3','/inputs/tools/qualification/core_selection/check.py','/work/build-core/CMakeCache.txt'],
 'selection-built':['python3','/inputs/tools/qualification/core_selection/check.py','/work/build-core/CMakeCache.txt'],
 'normalize-links':['python3','/inputs/output/output.py','normalize','/work','/work/plugin-normalization.json'],
 'install-audit':['python3','/inputs/tools/qualification/core_selection/after_install.py','/work'],
 'consumer-build':['sh','-c','cmake -S /consumer -B /consumer-output -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/work/install-core;/work/install-xacc" -DXACC_ROOT=/work/install-xacc && cmake --build /consumer-output --parallel 2'],
 'consumer-cpp':['/consumer-output/core-installed'],
 'consumer-python':['/work/python-core/bin/python','/consumer/core.py'],
 'installed-linkage':['sh','-c','ldd /consumer-output/core-installed; find /work/install-core/lib -name "*.so*" -type f -exec ldd {} \\;'],
}
for _name in ('antlr','python','configure','build','install'):
    COMMANDS[_name]=['sh','/inputs/native/stages.sh',_name]


def command(name,image):
    if name=='builder':return ['docker','build','--iidfile','/proof/builder-id','/proof/builder']
    cmd=['docker','run','--name','qb-core-'+name,'--network','none','--read-only','--cpus','2',
         '--memory','4g','--memory-swap','4g','--pids-limit','256','--cap-drop','ALL',
         '--security-opt','no-new-privileges','--user','65532:65532',
         '--tmpfs','/tmp:rw,exec,size=512m','--workdir','/tmp']
    if name in INSTALLED:
        for item in ('install-core','install-xacc','python-core'):
            cmd+=['--mount',f'type=bind,source=/work/native-work/{item},target=/work/{item},readonly']
        cmd+=['--mount','type=bind,source=/work/inputs/consumer,target=/consumer,readonly',
              '--mount','type=bind,source=/work/native-work/consumer-output,target=/consumer-output'+('' if name=='consumer-build' else ',readonly')]
    else:
        cmd+=['--mount','type=bind,source=/work/inputs,target=/inputs,readonly',
              '--mount','type=bind,source=/work/native-work,target=/work']
    return cmd+['--entrypoint','/usr/bin/env',image,'-i',
       'PATH=/work/python-core/bin:/usr/local/bin:/usr/bin:/bin','HOME=/tmp','OMP_NUM_THREADS=2',
       'OPENBLAS_NUM_THREADS=2','PYTHONDONTWRITEBYTECODE=1','PYTHONNOUSERSITE=1',
       'PYTHONPATH=/work/install-core/lib:/work/install-core/python-site']+COMMANDS[name]


def logs_from_archive(path,stages):
    logs={}
    with tarfile.open(path,'r|gz') as archive:
        for entry in archive:
            if entry.name not in {'logs/'+n+'.log' for n in stages}:continue
            if entry.name in logs or not entry.isfile() or not 0<=entry.size<=64*1024*1024:
                raise ValueError('invalid archived log')
            data=archive.extractfile(entry).read()
            name=entry.name[5:-4]
            if hashlib.sha256(data).hexdigest()!=stages[name]['log_sha256']:
                raise ValueError('archived log hash')
            logs[entry.name]=data.decode('utf-8',errors='strict')
    if len(logs)!=len(stages):raise ValueError('missing archived logs')
    return {n:logs['logs/'+n+'.log'] for n in stages}


def classify(report,protocol_path,archive_path):
    result={'schema':'qb.core-native-classification/v1','native_passed':False}
    if report.get('native_passed') is not True:
        return dict(result,reason='native report did not pass')
    try:
        raw=Path(protocol_path).read_bytes();protocol=json.loads(raw)
        if (report.get('kind')!='qb-core-native/v1' or report.get('error')
            or report.get('protocol_sha256')!=hashlib.sha256(raw).hexdigest()
            or report.get('materials_sha256')!=protocol['materials_sha256']
            or not re.fullmatch('[a-f0-9]{64}',report['materials_sha256'])):
            raise ValueError('protocol identity')
        image=report.get('builder_image','')
        if not re.fullmatch('sha256:[a-f0-9]{64}',image):raise ValueError('builder identity')
        stages=report['stages']
        if set(stages)!=set(STAGES):raise ValueError('stage set')
        for index,name in enumerate(STAGES):
            stage=stages[name]
            if (type(stage.get('index')) is not int or stage['index']!=index
                or type(stage.get('exit')) is not int or stage['exit']!=0
                or stage.get('timeout') is not False
                or (name!='builder' and stage.get('container_removed') is not True)
                or stage.get('command')!=command(name,image)):
                raise ValueError('stage contract: '+name)
        logs=logs_from_archive(archive_path,stages)
        inputs=json.loads(logs['verify-inputs'])
        if inputs.get('verified') is not True or inputs.get('manifest_sha256')!=report['materials_sha256']:
            raise ValueError('input material verification')
        for name in ('selection','selection-built'):
            selected=json.loads(logs[name])
            if (selected.get('actual_cpm_sources_verified') is not True
                or selected.get('input_audit',{}).get('passed') is not True):
                raise ValueError('selection audit')
        for name in ('source-audit','source-audit-built'):
            if json.loads(logs[name]).get('only_generated_header_changed') is not True:
                raise ValueError('source audit')
        if json.loads(logs['install-audit']).get('passed') is not True:
            raise ValueError('installed XACC baseline audit')
        if json.loads(logs['normalize-links']) != report.get('plugin_normalization'):
            raise ValueError('normalization report binding')
        for name,marker in [('xacc-replay','PASS: ACZ registered'),
             ('consumer-cpp','PASS: installed Core C++ QPP identity and Bell'),
             ('consumer-python','PASS: installed Core Python QPP identity and Bell')]:
            if marker not in logs[name] or '[error]' in logs[name]:raise ValueError('fixture marker')
        linkage=logs['installed-linkage']
        if (not linkage.strip() or any(x in linkage for x in
             ('not found','/work/build-core','/work/source-core','/work/build-xacc','/work/xacc','/opt/qb','/mnt/qb','/inputs'))):
            raise ValueError('installed linkage')
        return dict(result,native_passed=True,stages=len(STAGES),
                    scope='installed Core QPP C++ and Python identity/Bell; not hosted or all backends')
    except (ValueError,KeyError,TypeError,OSError,tarfile.TarError) as error:
        return dict(result,reason=str(error))
