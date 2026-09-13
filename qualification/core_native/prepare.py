"""Freeze verified Core build inputs; no package install, CMake or cloud execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(path):
    return json.loads(path.read_text())


def prepare(core, dependencies, xacc, python, output):
    import sys
    sys.path.insert(0, str(HERE.parent / 'source_provenance'))
    export = module('native_source_export', HERE.parent / 'source_provenance/export.py')
    archive = module('native_archive', HERE.parent / 'source_artifact/archive.py')
    roots = [Path(p).resolve() for p in (core, dependencies, xacc, python)]
    core, dependencies, xacc, python = roots
    output = Path(output).resolve()
    if output.exists() or any(output.is_relative_to(root) for root in roots):
        raise ValueError('output must be new and outside inputs')
    core_receipt = record(core / 'preparation.json')
    if (core_receipt['source_commit'] != 'a5c3e5fa544c07d538974d3a289b19652d483848'
            or sha(core / 'effective-source.json') != 'c5353f54ef26f65a21417516926ac3b027e766a0ecf20036400604dbcaffd405'):
        raise ValueError('Core identity')
    export.verify_tree(core / 'qristal-core', record(core / 'effective-source.json'))
    # Bind preparation to the independently retained actual dependency receipt.
    reference = HERE.parent / 'evidence/2026-09-13-core-dependencies/preparation.json'
    if (dependencies / 'preparation.json').read_bytes() != reference.read_bytes():
        raise ValueError('dependency preparation identity')
    dep = record(reference)
    for item in dep['dependencies']:
        manifest = dependencies / 'manifests' / (item['name'] + '.json')
        if sha(manifest) != item['effective_manifest_sha256']:
            raise ValueError('dependency manifest')
        export.verify_tree(dependencies / 'deps' / item['name'], record(manifest))
    if sha(dependencies / 'overrides.cmake') != dep['overrides_sha256']:
        raise ValueError('dependency overrides')
    for name, expected in dep['materials'].items():
        path = dependencies / ('patches/eigen.patch' if name == 'eigen.patch' else 'cache/cpm/' + name)
        if sha(path) != expected:
            raise ValueError('dependency material')
    report = record(xacc / 'recovered.json')
    report = report.get('result', report)
    if report['output_artifact']['sha256'] != 'b4569c7ca587c3a1fcbaa5e87a4606792c9a0904e2d15c5c2ef03a83b3088bb5':
        raise ValueError('XACC identity')
    archive.verify(xacc / 'archive.tar.gz', report['output_artifact'], {k:v for k,v in report.items() if k != 'output_artifact'})
    wheels = record(HERE.parent / 'evidence/2026-09-13-python-artifacts/core.json')['wheels']
    for wheel in wheels:
        name = wheel['filename']
        if Path(name).name != name or sha(python / 'core' / name) != wheel['sha256']:
            raise ValueError('Python wheel identity')
    antlr = record(HERE.parent / 'antlr_wheel/inputs.json')['artifacts']
    for name, expected in antlr.items():
        path = python / ('antlr-source' if name.endswith('.tar.gz') else 'core') / name
        if sha(path) != expected['sha256']:
            raise ValueError('ANTLR input identity')
    output.mkdir(parents=True)
    shutil.copytree(core / 'qristal-core', output / 'core', symlinks=True)
    export.verify_tree(output / 'core', record(core / 'effective-source.json'))
    shutil.copyfile(core / 'effective-source.json', output / 'core-manifest.json')
    (output / 'core-dependencies').mkdir()
    for name in ('deps', 'manifests', 'cache/cpm', 'patches'):
        (output / 'core-dependencies' / name).mkdir(parents=True)
    for item in dep['dependencies']:
        name = item['name']
        shutil.copytree(dependencies / 'deps' / name, output / 'core-dependencies/deps' / name, symlinks=True)
        shutil.copyfile(dependencies / 'manifests' / (name + '.json'), output / 'core-dependencies/manifests' / (name + '.json'))
    for relative in ('cache/cpm/CPM_0.36.0.cmake', 'patches/eigen.patch'):
        shutil.copyfile(dependencies / relative, output / 'core-dependencies' / relative)
    shutil.copyfile(dependencies / 'overrides.cmake', output / 'core-dependencies/overrides.cmake')
    shutil.copyfile(dependencies / 'preparation.json', output / 'core-dependencies/preparation.json')
    for item in dep['dependencies']:
        export.verify_tree(output / 'core-dependencies/deps' / item['name'], record(dependencies / 'manifests' / (item['name'] + '.json')))
    (output / 'xacc').mkdir()
    for name in ('archive.tar.gz', 'recovered.json'):
        shutil.copyfile(xacc / name, output / 'xacc' / name)
    archive.verify(output / 'xacc/archive.tar.gz', report['output_artifact'], {k:v for k,v in report.items() if k != 'output_artifact'})
    (output / 'python/wheels').mkdir(parents=True)
    for wheel in wheels:
        target = output / 'python/wheels' / wheel['filename']
        shutil.copyfile(python / 'core' / wheel['filename'], target)
        if sha(target) != wheel['sha256']: raise ValueError('copied Python wheel')
    shutil.copyfile(HERE.parent / 'evidence/2026-09-13-python-artifacts/core.json', output / 'python/core.json')
    (output / 'python/core.requirements.txt').write_text(''.join(w['name']+'=='+w['version']+' --hash=sha256:'+w['sha256']+'\n' for w in wheels))
    (output / 'antlr').mkdir()
    for name, expected in antlr.items():
        target = output / 'antlr' / name
        shutil.copyfile(python / ('antlr-source' if name.endswith('.tar.gz') else 'core') / name, target)
        if sha(target) != expected['sha256']: raise ValueError('copied ANTLR input')
    for name in ('recipe.py', 'inputs.json', 'build.sh'):
        shutil.copyfile(HERE.parent / 'antlr_wheel' / name, output / 'antlr' / name)
    (output / 'native').mkdir()
    for name in ('stages.sh','stage_work.py','verify_materials.py'):
        shutil.copyfile(HERE / name, output / 'native' / name)
    shutil.copytree(HERE / 'consumer', output / 'consumer')
    for relative in ('installed_inputs/prepare.py', 'source_artifact/archive.py'):
        target = output / 'tools/qualification' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(HERE.parent / relative, target)
    result = {'schema': 'qb.core-native-materials/v1', 'core_commit': core_receipt['source_commit'],
              'core_manifest_sha256': sha(output / 'core-manifest.json'),
              'dependency_receipt_sha256': sha(reference), 'xacc_archive_sha256': report['output_artifact']['sha256'],
              'wheel_count': len(wheels), 'python_lock_sha256': sha(output / 'python/core.requirements.txt'),
              'configured': False, 'built': False, 'executed': False}
    (output / 'materials.json').write_text(json.dumps(result, indent=2) + '\n')
    verifier = module('native_material_verifier', HERE / 'verify_materials.py')
    manifest = {'schema': 'qb.core-material-manifest/v1', 'entries': verifier.inventory(output, exclude_manifest=True)}
    (output / 'material-manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    result['material_verification'] = verifier.verify(output)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('core','dependencies','xacc','python','output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.core,args.dependencies,args.xacc,args.python,args.output),indent=2))
