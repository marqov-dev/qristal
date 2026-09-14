"""Disposable VM entry point: execute frozen probes and upload bounded evidence."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zlib

ROOT=Path('/work')


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    console={'kind':'qb-qpp-native-image/v1','native_passed':False}
    try:
        protocol=json.loads((ROOT/'cloud-protocol.json').read_text())
        console['protocol_sha256']=protocol['native_protocol_sha256']
        for name in ('guest.py','native_image_evidence.py'):
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=protocol['files'][name]['sha256']:
                raise ValueError('guest source identity')
        runner=module('native_image',ROOT/'native/qualification/core_package/native_image.py')
        evidence=module('native_image_evidence',ROOT/'native_image_evidence.py')
        result_dir=Path('/proof/native-result')
        result=runner.execute(ROOT/'native',result_dir,protocol['native_protocol_sha256'])
        output=Path('/proof/native-image-report.json')
        identity=evidence.pack(result_dir,ROOT/'native/protocol.json',output)
        code=subprocess.run(['curl','--config','/proof/output-put.conf','--silent','--fail',
                             '--max-time','120','--upload-file',str(output)],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=135).returncode
        if code:raise RuntimeError('report upload failed')
        console.update(output_artifact=identity,native_passed=result.get('passed') is True)
    except Exception as error:
        console['error']=type(error).__name__
    finally:
        Path('/proof/output-put.conf').unlink(missing_ok=True)
    raw=json.dumps(console,sort_keys=True,separators=(',',':')).encode()
    encoded=base64.b64encode(zlib.compress(raw)).decode()
    if len(encoded)>128*160:raise ValueError('console reference size')
    parts=[encoded[i:i+160] for i in range(0,len(encoded),160)]
    for _ in range(2):
        for i,part in enumerate(parts):print('QB_ADAPTER_CHUNK',hashlib.sha256(raw).hexdigest(),i,len(parts),part,flush=True)


if __name__=='__main__':main()
