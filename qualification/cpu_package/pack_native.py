"""Package only checked CPU context and named native harness inputs."""
import argparse
import json
from pathlib import Path
import tarfile

import stage

HERE = Path(__file__).resolve().parent


def pack(context, output):
    stage.verify_context(context)
    if output.resolve().is_relative_to(context.resolve()):
        raise ValueError('archive output must be outside context')
    output.mkdir(parents=True, exist_ok=False)
    files = {'stage.py': HERE / 'stage.py', 'guest.py': HERE / 'guest.py',
             'qristal/qualification/runtime/test_image.py': HERE.parent / 'runtime/test_image.py'}
    manifest = {'schema': 'marqov.cpu-native-input/v1',
                'context_sha256': stage.sha(context / 'context.json'),
                'files': {name: stage.sha(path) for name, path in files.items()}}
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    archive = output / 'cpu.tar.gz'
    with tarfile.open(archive, 'w:gz', dereference=False) as stream:
        stream.add(context, arcname='context')
        for name, path in files.items():
            stream.add(path, arcname=name)
        stream.add(manifest_path, arcname='manifest.json')
    (output / 'archive.json').write_text(json.dumps({'sha256': stage.sha(archive),
                                                   'bytes': archive.stat().st_size}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('context', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    pack(args.context, args.output)
