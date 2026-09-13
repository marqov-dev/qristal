"""Prepare reviewed Core source transformations; never configure or build it."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import difflib
import version
import dependency_path

HERE = Path(__file__).resolve().parent
SOURCE_COMMIT = 'a5c3e5fa544c07d538974d3a289b19652d483848'
RECEIPT_SHA256 = '904ae7ddb228aac54027ad313ae1d9a28f927479297b4e978145abcbc888d642'
DEPENDENCIES_SHA256 = 'ffd6f15444d7dd885b38a66b23651eee535a49f931f331226fe01507d7e43840'
OLD = b'set(Eigen3_INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/deps/eigen3)\n'
NEW = b'set(Eigen3_INSTALL_DIR ${CMAKE_CURRENT_BINARY_DIR}/deps/eigen3)\n'
PATCH = (b'--- a/cmake/dependencies.cmake\n+++ b/cmake/dependencies.cmake\n'
         b'@@ -88 +88 @@\n-' + OLD + b'+' + NEW)
sys.path.insert(0, str(HERE.parent / 'source_provenance'))
spec = importlib.util.spec_from_file_location('core_source_export', HERE.parent / 'source_provenance/export.py')
source_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source_export)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def transform(data):
    if sha(data) != DEPENDENCIES_SHA256 or data.count(OLD) != 1:
        raise ValueError('unexpected locked dependency source')
    return data.replace(OLD, NEW, 1)


def prepare(inputs, output):
    inputs, output = Path(inputs).resolve(), Path(output).resolve()
    if output.is_relative_to(inputs) or output.exists():
        raise ValueError('output must be new and outside inputs')
    receipt_path = inputs / 'core-source.json'
    if receipt_path.is_symlink():
        raise ValueError('source receipt must be a regular file')
    raw = receipt_path.read_bytes()
    if sha(raw) != RECEIPT_SHA256:
        raise ValueError('unapproved source receipt')
    receipt = json.loads(raw)
    if receipt['source']['commit'] != SOURCE_COMMIT:
        raise ValueError('locked Core revision')
    source = inputs / 'qristal-core'
    source_export.verify_tree(source, receipt['source'])
    patch = (HERE / 'eigen-build-staging.patch').read_bytes()
    if patch != PATCH:
        raise ValueError('unexpected transformation patch')
    original = (source / 'cmake/dependencies.cmake').read_bytes()
    changed = transform(original)
    original_version = (source / 'CMakeLists.txt').read_bytes()
    changed_version = version.transform(original_version)
    version_patch = (HERE / 'exported-version.patch').read_bytes()
    expected_patch = ''.join(difflib.unified_diff(original_version.decode().splitlines(True),
        changed_version.decode().splitlines(True), fromfile='a/CMakeLists.txt', tofile='b/CMakeLists.txt')).encode()
    if version_patch != expected_patch:
        raise ValueError('unexpected version patch')
    original_path = (source / 'cmake/add_dependency.cmake').read_bytes()
    changed_path = dependency_path.transform(original_path)
    path_patch = (HERE / 'dependency-path-guard.patch').read_bytes()
    expected_path_patch = ''.join(difflib.unified_diff(original_path.decode().splitlines(True),
        changed_path.decode().splitlines(True), fromfile='a/cmake/add_dependency.cmake',
        tofile='b/cmake/add_dependency.cmake', n=0)).encode()
    if path_patch != expected_path_patch:
        raise ValueError('unexpected dependency path patch')
    output.mkdir(parents=True)
    derived = output / 'qristal-core'
    shutil.copytree(source, derived, symlinks=True)
    # Verify the copied bytes before transforming; never reuse or edit inputs.
    source_export.verify_tree(derived, receipt['source'])
    (derived / 'cmake/dependencies.cmake').write_bytes(changed)
    (derived / 'CMakeLists.txt').write_bytes(changed_version)
    (derived / 'cmake/add_dependency.cmake').write_bytes(changed_path)
    effective = json.loads(json.dumps(receipt['source']))
    entry = next(e for e in effective['entries'] if e['path'] == 'cmake/dependencies.cmake')
    entry.update(sha256=sha(changed), bytes=len(changed))
    # This is an effective byte manifest, not a claim that these are Git-tree bytes.
    effective.pop('commit')
    effective.pop('tree')
    entry.pop('git_blob')
    version_entry = next(e for e in effective['entries'] if e['path'] == 'CMakeLists.txt')
    version_entry.update(sha256=sha(changed_version), bytes=len(changed_version))
    version_entry.pop('git_blob')
    path_entry = next(e for e in effective['entries'] if e['path'] == 'cmake/add_dependency.cmake')
    path_entry.update(sha256=sha(changed_path), bytes=len(changed_path))
    path_entry.pop('git_blob')
    source_export.verify_tree(derived, effective)
    effective_bytes = (json.dumps(effective, sort_keys=True, indent=2) + '\n').encode()
    (output / 'effective-source.json').write_bytes(effective_bytes)
    record = {'schema': 'marqov.core-preparation/v1', 'source_commit': SOURCE_COMMIT,
              'source_receipt_sha256': sha(raw), 'patch_sha256': sha(patch),
              'transformation': 'Eigen temporary install moved to Core binary directory',
              'source_version': '1.8.1', 'version_patch_sha256': sha(version_patch),
              'original_version_file_sha256': sha(original_version),
              'derived_version_file_sha256': sha(changed_version),
              'original_dependency_sha256': sha(original), 'derived_dependency_sha256': sha(changed),
              'dependency_path_patch_sha256': sha(path_patch),
              'original_dependency_path_sha256': sha(original_path), 'derived_dependency_path_sha256': sha(changed_path),
              'effective_manifest_sha256': sha(effective_bytes),
              'configured': False, 'native_qualified': False, 'published': False,
              'remaining_blockers': ['offline dependency selection',
                                     'hashed Python wheelhouse', 'retained fresh XACC install']}
    (output / 'preparation.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    print(json.dumps(prepare(a.inputs, a.output), indent=2))
