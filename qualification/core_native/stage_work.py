"""Stage disposable native work copies from frozen inputs; execute no workload."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from verify_materials import verify, inventory


def audit_core(original, derived):
    before, after = inventory(original), inventory(derived)
    allowed = 'include/qristal/core/cmake_variables.hpp'
    generated = after.pop(allowed, None)
    before.pop(allowed, None)
    if before != after or not generated or generated['type'] != 'file':
        raise ValueError('unexpected Core source mutation')
    return {'only_generated_header_changed': True, 'generated_header': generated}


def stage(inputs, work):
    if sys.platform != 'linux':
        raise ValueError('native materialization requires Linux')
    verify(inputs)
    destinations = ('source-core','core-dependencies','extracted-xacc','install-xacc')
    if any((work/name).exists() or (work/name).is_symlink() for name in destinations):
        raise ValueError('work destinations must be new')
    shutil.copytree(inputs/'core', work/'source-core', symlinks=True)
    shutil.copytree(inputs/'core-dependencies', work/'core-dependencies', symlinks=True)
    if inventory(inputs/'core') != inventory(work/'source-core') or inventory(inputs/'core-dependencies') != inventory(work/'core-dependencies'):
        raise ValueError('work-copy identity')
    spec=importlib.util.spec_from_file_location('native_installed_inputs', inputs/'tools/qualification/installed_inputs/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.prepare(inputs/'xacc/archive.tar.gz',json.loads((inputs/'xacc/recovered.json').read_text()),work/'extracted-xacc')
    shutil.copytree(work/'extracted-xacc/tree/install-xacc',work/'install-xacc',symlinks=True)
    if inventory(work/'extracted-xacc/tree/install-xacc') != inventory(work/'install-xacc'):
        raise ValueError('XACC derivative identity')
    return {'staged':True,'executed':False}


if __name__ == '__main__':
    if sys.argv[1:] == ['audit-core']:
        result=audit_core(Path('/inputs/core'),Path('/work/source-core'))
    elif sys.argv[1:] == ['stage']:
        result=stage(Path('/inputs'),Path('/work'))
    else:
        raise SystemExit('select stage or audit-core')
    print(json.dumps(result,sort_keys=True))
