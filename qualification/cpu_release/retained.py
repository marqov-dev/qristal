"""Replay retained CPU registry records, including losslessly compressed SPDX."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('retained_cpu_verifier',HERE/'verify.py')
verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)


def verify(root):
    record=json.loads((root/'records.json').read_text())
    required={'release.json','release-context.json','registry-index.json','platform-manifest.json','image-inspect.json',
              'build-metadata.json','inventory.json','sbom.json','provenance.json','verification.json',
              'input-draft.json','workflow.json','package-visibility.json','acquired/image-tests.json','acquired/image-reject-gpu.log'}
    if record['schema']!='marqov.cpu-retained-release/v1' or not required <= set(record['records']):
        raise ValueError('retained_record_set')
    for name,item in record['records'].items():
        if item['stored_file'] not in (name,name+'.gz') or Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('record_path')
        alternate=name if item['stored_file']==name+'.gz' else name+'.gz'
        if (root/alternate).exists():raise ValueError('ambiguous_stored_record')
        raw=(root/item['stored_file']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item['stored_sha256']:raise ValueError('stored_bytes')
        if item['stored_file'].endswith('.gz'):raw=gzip.decompress(raw)
        if len(raw)!=item['bytes'] or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('original_bytes')
    def read(name):return json.loads((root/name).read_text())
    workflow,release=read('workflow.json'),read('release.json')
    if workflow['conclusion']!='success' or workflow['status']!='completed' or workflow['headSha']!=release['source_revision']:
        raise ValueError('workflow_result')
    if release['workflow_run']!=workflow['url']+'/attempts/1':raise ValueError('workflow_identity')
    draft=read('input-draft.json');parent=release['context']['parent']
    if draft['draft'] is not True or draft['tag']!=parent['draft_release_tag'] or len(draft['assets'])!=1:
        raise ValueError('draft_state')
    asset=draft['assets'][0]
    if asset['name']!=parent['asset_name'] or asset['digest']!='sha256:'+parent['archive_sha256'] or asset['state']!='uploaded':
        raise ValueError('draft_asset')
    visibility=read('package-visibility.json')
    if visibility['name']!='qristal-cpu' or visibility['visibility']!='private':raise ValueError('package_visibility')
    result=verifier.verify(root)
    if result!=read('verification.json'):raise ValueError('retained_verdict')
    return result


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1])),indent=2))
