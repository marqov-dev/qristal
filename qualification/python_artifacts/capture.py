"""Inventory downloaded wheels and check base dependency metadata for Linux3.10.

Requires packaging on the operator interpreter; does not install/import wheels.
This metadata check excludes optional extras and is not native pip-check evidence.
"""
import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import packaging
from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def capture(root):
    environment=default_environment()
    environment.update(python_version='3.10',python_full_version='3.10.12',
        sys_platform='linux',platform_system='Linux',platform_machine='x86_64',
        implementation_name='cpython',implementation_version='3.10.12',extra='')
    wheels=[];versions={}
    for path in sorted(Path(root).glob('*.whl')):
        with ZipFile(path) as archive:
            entries=[n for n in archive.namelist() if n.endswith('.dist-info/METADATA')]
            if len(entries)!=1:raise ValueError('wheel metadata')
            metadata=BytesParser().parsebytes(archive.read(entries[0]))
        name=canonicalize_name(metadata['Name']); version=metadata['Version']
        if name in versions:raise ValueError('duplicate distribution')
        versions[name]=version
        wheels.append(dict(name=name,version=version,filename=path.name,
            bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            requires_python=metadata.get('Requires-Python'),requires_dist=metadata.get_all('Requires-Dist',[])))
    unmet=[]
    for wheel in wheels:
        for text in wheel['requires_dist']:
            requirement=Requirement(text)
            if requirement.marker and not requirement.marker.evaluate(environment):continue
            found=versions.get(canonicalize_name(requirement.name))
            if found is None or not requirement.specifier.contains(found):
                unmet.append(dict(package=wheel['name'],requires=str(requirement),found=found))
    return dict(schema='qb.python-artifact-inputs/v1',target=environment,
        metadata_checker_packaging_version=packaging.__version__,wheels=wheels,
        unmet_base_requirements=unmet,installed=False,native_qualified=False)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args(); data=capture(args.root)
    with args.output.open('x') as stream:stream.write(json.dumps(data,indent=2)+'\n')
    lock='\n'.join(x['name']+'=='+x['version']+' --hash=sha256:'+x['sha256'] for x in data['wheels'])+'\n'
    with args.output.with_suffix('.requirements.txt').open('x') as stream:stream.write(lock)
    print(json.dumps({'wheels':len(data['wheels']),'unmet':data['unmet_base_requirements']}))
