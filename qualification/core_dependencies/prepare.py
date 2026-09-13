"""Prepare verified offline C++ source overrides; never run CMake or acquisition."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'source_provenance'))
spec = importlib.util.spec_from_file_location('dependency_export', HERE.parent / 'source_provenance/export.py')
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)
EIGEN_FILES = {'Eigen/Core', 'Eigen/src/Core/arch/NEON/Complex.h',
               'Eigen/src/Core/products/GeneralMatrixMatrix.h', 'Eigen/src/Core/products/Parallelizer.h'}
NAMES = {'nlohmann_json','autodiff','cpr','pybind11','eigen3','yamlcpp','range-v3',
         'cppitertools','googletest','cereal','args'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('expected regular input file')
    return path.read_bytes()


def validate_lock(lock):
    items = lock['dependencies']
    if (lock['schema'] != 'marqov.core-dependency-lock/v1' or len(items) != len(NAMES)
            or {item['name'] for item in items} != NAMES
            or set(lock['materials']) != {'eigen.patch','CPM_0.36.0.cmake'}):
        raise ValueError('dependency lock schema')
    for item in items:
        expected_name = 'Eigen3' if item['name'] == 'eigen3' else item['name']
        if (item['cpm_name'] != expected_name or not re.fullmatch('[a-f0-9]{40}',item['commit'])
                or not re.fullmatch('[a-f0-9]{64}',item['receipt_sha256'])):
            raise ValueError('dependency lock identity')


def overrides(items):
    lines = ['# Source selections only; configure must verify actual system/CPM resolution.',
             'set(CPM_SOURCE_CACHE "${CMAKE_CURRENT_LIST_DIR}/cache" CACHE PATH "Captured CPM cache" FORCE)']
    for item in items:
        lines.append('set(CPM_' + item['cpm_name'] + '_SOURCE "${CMAKE_CURRENT_LIST_DIR}/deps/'
                     + item['name'] + '" CACHE PATH "Verified source override" FORCE)')
    return '\n'.join(lines) + '\n'


def apply_eigen(target, patch):
    # Both patch and pristine target were verified before entering this function.
    env = {k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    command = ['git', '-c', 'core.fsmonitor=false', 'apply']
    for options in (['--check'], []):
        subprocess.run(command + options + [str(patch.resolve())], cwd=target, env=env,
                       capture_output=True, check=True, timeout=30)


def prepare(inputs, output):
    inputs = Path(inputs).resolve()
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(inputs):
        raise ValueError('output must be new and outside input tree')
    lock_raw = read_regular(HERE / 'lock.json')
    lock = json.loads(lock_raw)
    validate_lock(lock)
    # Reject replacement parent links as well as replacement leaf files.
    for name in ('receipts', 'deps', 'qualification-inputs'):
        path = inputs / name
        if path.is_symlink() or not path.is_dir():
            raise ValueError('unexpected input directory')
    receipts = {}
    for item in lock['dependencies']:
        raw = read_regular(inputs / 'receipts' / (item['name'] + '.json'))
        if digest(raw) != item['receipt_sha256']:
            raise ValueError('dependency receipt binding')
        source = json.loads(raw)['source']
        if source['commit'] != item['commit']:
            raise ValueError('dependency commit binding')
        export.verify_tree(inputs / 'deps' / item['name'], source)
        receipts[item['name']] = source
    materials = {}
    for name, expected in lock['materials'].items():
        raw = read_regular(inputs / 'qualification-inputs' / name)
        if digest(raw) != expected:
            raise ValueError('material binding')
        materials[name] = raw
    output.mkdir(parents=True)
    (output / 'deps').mkdir()
    (output / 'manifests').mkdir()
    (output / 'patches').mkdir()
    (output / 'cache/cpm').mkdir(parents=True)
    (output / 'cache/cpm/CPM_0.36.0.cmake').write_bytes(materials['CPM_0.36.0.cmake'])
    patch = output / 'patches/eigen.patch'
    patch.write_bytes(materials['eigen.patch'])
    observations = []
    for item in lock['dependencies']:
        name = item['name']
        target = output / 'deps' / name
        shutil.copytree(inputs / 'deps' / name, target, symlinks=True)
        export.verify_tree(target, receipts[name])
        effective = copy.deepcopy(receipts[name])
        effective.pop('commit'); effective.pop('tree')
        changes = []
        if name == 'eigen3':
            apply_eigen(target, patch)
            for entry in effective['entries']:
                if entry['path'] not in EIGEN_FILES:
                    continue
                raw = read_regular(target / entry['path'])
                changed = digest(raw)
                if changed == entry['sha256']:
                    raise ValueError('expected Eigen patch modification missing')
                changes.append({'path':entry['path'], 'before':entry['sha256'], 'after':changed})
                entry.update(sha256=changed, bytes=len(raw))
                entry.pop('git_blob')
            if {c['path'] for c in changes} != EIGEN_FILES:
                raise ValueError('Eigen patch scope')
        export.verify_tree(target, effective)
        data = (json.dumps(effective, sort_keys=True, indent=2) + '\n').encode()
        (output / 'manifests' / (name + '.json')).write_bytes(data)
        observations.append(dict(item, effective_manifest_sha256=digest(data), changes=changes))
    config = overrides(lock['dependencies']).encode()
    (output / 'overrides.cmake').write_bytes(config)
    report = {'schema':'marqov.core-dependency-preparation/v1', 'lock_sha256':digest(lock_raw),
              'core_commit':lock['core_commit'], 'dependencies':observations,
              'materials':lock['materials'], 'overrides_sha256':digest(config),
              'configured':False, 'native_qualified':False, 'published':False,
              'actual_dependency_selection_verified':False}
    (output / 'preparation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs',type=Path); p.add_argument('output',type=Path)
    args = p.parse_args()
    print(json.dumps(prepare(args.inputs,args.output),indent=2))
