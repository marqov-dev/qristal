"""Derive a checked release context from the fixed, previously tested input archive."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tarfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cpu_staging', HERE.parent/'cpu_package/stage.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def prepare(archive, output, revision, inputs=None):
    if not re.fullmatch('[a-f0-9]{40}',revision):
        raise ValueError('source_revision')
    expected = inputs if inputs is not None else json.loads((HERE/'inputs.json').read_text())
    if stage.sha(archive) != expected['archive_sha256']:
        raise ValueError('archive_binding')
    output.mkdir(parents=True,exist_ok=False)
    # Extract directories/files first; create links only after verifying the
    # declared payload, never write through an archive-provided symlink.
    with tarfile.open(archive,'r:gz') as stream:
        members = [m for m in stream.getmembers() if m.name == 'context' or m.name.startswith('context/')]
        names = set()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or member.name in names or not (member.isdir() or member.isfile() or member.issym()):
                raise ValueError('archive_member')
            names.add(member.name)
        for member in members:
            if member.issym():continue
            target = output/Path(member.name)
            target.parent.mkdir(parents=True,exist_ok=True)
            if member.isdir():target.mkdir(exist_ok=True)
            else:
                with stream.extractfile(member) as source, target.open('xb') as dest:
                    shutil.copyfileobj(source,dest)
            target.chmod(member.mode)
        for member in members:
            if member.issym():
                (output/member.name).symlink_to(member.linkname)
    context = output/'context'
    stage.verify_context(context)
    if stage.sha(context/'context.json') != expected['context_sha256']:
        raise ValueError('context_binding')
    shutil.copy2(HERE/'inventory.py', context/'payload/opt/qristal/inventory.py')
    (context/'payload/opt/qristal/inventory.py').chmod(0o644)
    with (context/'Dockerfile').open('a') as f:
        f.write('\nLABEL org.opencontainers.image.source="https://github.com/marqov-dev/qristal"\n')
        f.write(f'LABEL org.opencontainers.image.revision="{revision}"\n')
    (context/'payload-inventory.json').write_text(json.dumps(stage.inventory(context/'payload'),indent=2)+'\n')
    record = json.loads((context/'context.json').read_text())
    record['files'] = {name:stage.sha(context/name) for name in record['files']}
    (context/'context.json').write_text(json.dumps(record,indent=2)+'\n')
    stage.verify_context(context)
    (output/'release-context.json').write_text(json.dumps({'schema':'marqov.cpu-release-context/v1',
        'source_revision':revision,'parent':expected,'context':record,
        'inventory_sha256':stage.sha(HERE/'inventory.py'),
        'payload_hashes':{name:stage.sha(context/'payload/opt/qristal'/name) for name in ('runtime.py','adapter.py','capabilities.json')},
        'matrix_sha256':stage.sha(HERE/'matrix.py'),
        'installed_binary_origin':'unverified'},indent=2)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('archive',type=Path);p.add_argument('output',type=Path);p.add_argument('--revision',required=True)
    a=p.parse_args();prepare(a.archive,a.output,a.revision)
