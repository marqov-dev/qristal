"""Bind QPP runtime assets to staging; does not install or build anything."""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def attach(context, plan):
    """Called inside stage's private output before publishing a new directory."""
    context = Path(context)
    root = context / 'runtime'
    root.mkdir()
    sources = {name: HERE.parent / 'runtime' / name for name in ('adapter.py', 'runtime.py')}
    sources.update({name: HERE / 'runtime' / name for name in
                    ('qpp_runtime.py', 'capabilities.json', 'install-python.sh')})
    bindings = {}
    for name, source in sources.items():
        raw = source.read_bytes()
        (root / name).write_bytes(raw)
        bindings[name] = hashlib.sha256(raw).hexdigest()
    (root / 'empty-backends.yaml').write_text('{}\n')
    requirements = []
    wheels = list(plan['required_python']['wheels'])
    antlr = plan['required_python']['antlr']
    wheels.append(dict(antlr, filename=Path(antlr['archive_path']).name))
    for item in wheels:
        name, digest = item['filename'], item['sha256']
        if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.whl', name) or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('unsafe wheel requirement')
        requirements.append('/inputs/wheels/' + name + ' --hash=sha256:' + digest)
    raw = ('\n'.join(requirements) + '\n').encode()
    (root / 'requirements.txt').write_bytes(raw)
    bindings['requirements.txt'] = hashlib.sha256(raw).hexdigest()
    bindings['empty-backends.yaml'] = hashlib.sha256(b'{}\n').hexdigest()
    result = {
        'schema': 'qb.core-runtime-recipe/v1', 'assets_sha256': bindings,
        'source_artifact_sha256': plan['bindings']['archive_sha256'],
        'evidence_provenance': plan['evidence_provenance'],
        'runtime_built': False, 'runtime_qualified': False, 'hosted': False,
        'build_ready': False,
        'blocked_on': 'acquire and bind final linux/amd64 OS package closure and notices',
        'install_layout': {'work.tar': 'extract validated payload into /work on case-sensitive Linux', 'python/wheels': '/inputs/wheels',
                           'runtime/requirements.txt': '/inputs/requirements.txt',
                           'runtime': '/opt/qristal'},
        'entrypoint': ['/work/python-core/bin/python', '/opt/qristal/qpp_runtime.py'],
        'environment': {'PYTHONPATH': '/work/install-core/lib:/work/install-core/python-site',
                        'HOME': '/tmp', 'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                        'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2'},
        'isolation': {'user': '65532:65532', 'network': 'none', 'read_only': True,
                      'cpus': 2, 'memory_bytes': 4294967296, 'pids': 256,
                      'cap_drop': 'ALL', 'no_new_privileges': True},
        'next_validation': ['OS/Python ABI and pip check', 'installed-only identity and Bell',
                            'QPP CLI JSON counts and bit order', 'Aer and noise rejected before native import',
                            'no source/build mounts; read-only nonroot networkless limits',
                            'full notices and acquired image-digest replay'],
    }
    (context / 'runtime-recipe.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
