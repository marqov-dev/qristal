"""Inventory installed CPU package metadata and notices, without importing engines."""
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    environments = {}
    for name, paths in {'core':['/runtime/python-core','/work/install-core/lib'],
                        'integrations':['/runtime/python-integration','/work/install-integrations']}.items():
        packages = []
        for dist in metadata.distributions(path=paths):
            if not dist.metadata.get('Name') or not dist.version:
                raise ValueError('incomplete_distribution_metadata')
            packages.append({'name':dist.metadata['Name'],'version':dist.version})
        environments[name] = sorted(packages,key=lambda p:(p['name'],p['version']))
    notices = []
    for root in ('/opt/qristal/licenses','/usr/share/doc'):
        for directory, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if not (Path(directory)/d).is_symlink())
            for name in sorted(files):
                path = Path(directory)/name
                if not path.is_symlink() and any(term in name.lower() for term in ('license','notice','copyright','copying')):
                    notices.append({'path':str(path),'sha256':digest(path)})
    return {'schema':'marqov.cpu-inventory/v1','python':platform.python_version(),
            'architecture':platform.machine(),'uid':os.getuid(),'python_environments':environments,
            'dpkg':subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],text=True,timeout=30),
            'notices':notices,'source_license_sha256':digest(Path('/opt/qristal/LICENSE.source')),
            'payload':{name:digest(Path('/opt/qristal')/name) for name in ('runtime.py','adapter.py','capabilities.json','inventory.py')},
            'build_origin':'observed_installed_bytes_not_verified_build_origin'}


if __name__ == '__main__':
    print(json.dumps(collect(),sort_keys=True))
