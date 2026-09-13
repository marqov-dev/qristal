"""Check the catalog against retained observations; never acquire or run images."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def verify(catalog, root=ROOT):
    if catalog['schema'] != 'marqov.runtime-catalog/v1' or catalog['hosted_available'] is not False:
        raise ValueError('catalog boundary')
    for name, expected in catalog['records'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('record binding')
    artifacts = catalog['artifacts']
    by_id = {artifact['id']:artifact for artifact in artifacts}
    if len(by_id)!=len(artifacts) or set(by_id)!={'cpu-local-2026-09-09','cudaq-gpu-2026-09-11','cpu-registry-2026-09-13'}:
        raise ValueError('artifact set')
    cpu, gpu = by_id['cpu-local-2026-09-09'], by_id['cudaq-gpu-2026-09-11']
    for artifact in artifacts:
        for key in ('evidence', 'qualification'):
            if artifact[key] not in catalog['records']:
                raise ValueError('unbound record')
    receipt = json.loads((root / cpu['evidence']).read_text())
    tests = json.loads((root / cpu['qualification']).read_text())
    if (cpu['identity'] != receipt['image'] or tests['image'] != receipt['image']
            or receipt['published'] is not False or cpu['access'] != 'local_only'
            or cpu['identity_kind'] != 'local_image_configuration'):
        raise ValueError('cpu identity/access')
    if cpu['capabilities'] not in catalog['records'] or tests['no_host_mounts'] is not True:
        raise ValueError('cpu scope')
    names = {t['name'] for t in tests['tests']}
    if names != {'capabilities','core','noise','integration','decoder','bell','noisy-bell','reject-shots','reject-gpu','isolation'}:
        raise ValueError('cpu test set')
    for test in tests['tests']:
        if test['exit'] != (2 if test['name'].startswith('reject-') else 0):
            raise ValueError('cpu test result')
    receipt = json.loads((root / gpu['evidence']).read_text())
    report = json.loads((root / gpu['qualification']).read_text())
    if (gpu['identity'] != receipt['image'] or gpu['identity'] != report['build']['release_binding']['registry_image']
            or gpu['access'] != 'private_registry' or gpu['identity_kind'] != 'registry_index'):
        raise ValueError('gpu identity/access')

    published = by_id['cpu-registry-2026-09-13']
    for key in ('evidence','qualification','capabilities','inventory','visibility','records'):
        if published[key] not in catalog['records']:
            raise ValueError('unbound cpu release record')
    bundle=Path(published['evidence']).parent
    for key,filename in {'evidence':'release.json','qualification':'verification.json','capabilities':'acquired/image-capabilities.log',
                         'inventory':'inventory.json','visibility':'package-visibility.json','records':'records.json'}.items():
        if published[key]!=str(bundle/filename):raise ValueError('cpu bundle pointer')
    receipt=json.loads((root/published['evidence']).read_text())
    report=json.loads((root/published['qualification']).read_text())
    if (published['identity']!=receipt['image'] or published['identity']!=report['registry_image']
            or published['access']!='private_registry' or published['identity_kind']!='registry_index'
            or report['native_passed'] is not True or report['backend_rejection_verified'] is not True
            or report['inventory_exported'] is not True or report['hosted_available'] is not False):
        raise ValueError('published cpu qualification')
    spec=importlib.util.spec_from_file_location('catalog_cpu_retained',ROOT/'cpu_release/retained.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    if checker.verify((root/published['evidence']).parent)!=report:
        raise ValueError('published cpu evidence')


def main():
    verify(json.loads((ROOT / 'distribution/catalog.json').read_text()))
    subprocess.run([sys.executable, '-B', str(ROOT / 'gpu_release/check_native.py'),
                    str(ROOT / 'evidence/2026-09-11-gpu-published')], check=True, timeout=120)
    print('PASS: catalog matches retained evidence; no new execution or public release implied')


if __name__ == '__main__':
    main()
