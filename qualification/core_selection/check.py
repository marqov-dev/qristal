"""Check actual CPM cache selections and pre-install mutable-input boundaries."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

HERE = Path(__file__).resolve().parent
PACKAGES = {'nlohmann_json':'nlohmann_json','autodiff':'autodiff','cpr':'cpr',
            'pybind11':'pybind11','eigen3':'Eigen3','yamlcpp':'yamlcpp',
            'range-v3':'range-v3','cppitertools':'cppitertools',
            'googletest':'googletest','cereal':'cereal','args':'args'}
FIND_NAMES = ('Eigen3','pybind11','yaml-cpp','GTest','nlohmann_json','range-v3',
              'autodiff','cereal','args','cpr','cppitertools')


def cache_entries(text):
    result = {}
    for line in text.splitlines():
        if not line or line.startswith(('#','//')): continue
        match = re.fullmatch(r'([^:=]+):([^=]+)=(.*)', line)
        if not match: raise ValueError('malformed cache entry')
        name, kind, value = match.groups()
        if name in result: raise ValueError('duplicate cache entry')
        result[name] = (kind,value)
    return result


def selections(text):
    cache = cache_entries(text)
    observed = {}
    for name, cpm in PACKAGES.items():
        key = 'CPM_PACKAGE_' + cpm + '_SOURCE_DIR'
        expected = '/work/core-dependencies/deps/' + name
        if cache.get(key) != ('INTERNAL',expected):
            raise ValueError('actual CPM source selection: '+name)
        binary = cache.get('CPM_PACKAGE_'+cpm+'_BINARY_DIR', ('',''))
        path = PurePosixPath(binary[1])
        if (binary[0] != 'INTERNAL' or str(path) != binary[1] or '..' in path.parts
                or not path.is_relative_to('/work/build-core') or str(path) == '/work/build-core'):
            raise ValueError('CPM build output: '+name)
        observed[name] = {'source':expected,'binary':binary[1]}
    for name in FIND_NAMES:
        if cache.get('CMAKE_DISABLE_FIND_PACKAGE_'+name) != ('BOOL','TRUE'):
            raise ValueError('find-package gate: '+name)
    for name, value in {'XACC_DIR':'/work/install-xacc','XACC_ROOT':'/work/install-xacc',
                        'CMAKE_HOME_DIRECTORY':'/work/source-core',
                        'CMAKE_INSTALL_PREFIX':'/work/install-core'}.items():
        if cache.get(name, ('',''))[1] != value: raise ValueError('prefix selection: '+name)
    return {'schema':'qb.core-selection/v1','cpm_sources':observed,
            'actual_cpm_sources_verified':True,'target_linkage_verified':False,
            'system_package_versions_qualified':False}


def native_helpers():
    sys.path.insert(0,str(HERE.parent/'core_native'))
    spec=importlib.util.spec_from_file_location('selection_stage_work',HERE.parent/'core_native/stage_work.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    return helper


def audit(inputs,work):
    helper=native_helpers()
    core=helper.audit_core(inputs/'core',work/'source-core')
    dependencies={}
    for name in PACKAGES:
        before=helper.inventory(inputs/'core-dependencies/deps'/name)
        after=helper.inventory(work/'core-dependencies/deps'/name)
        changes={n:{'before':before.get(n),'after':after.get(n)}
                 for n in sorted(set(before)|set(after)) if before.get(n)!=after.get(n)}
        dependencies[name]={'changes':changes,'unchanged':not changes}
    # CPM cache/build metadata is outside source trees and intentionally mutable.
    # No unexpected dependency source changes are silently promoted to provenance.
    spec=importlib.util.spec_from_file_location('selection_original_entries',HERE/'after_install.py')
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    xacc_before=baseline.original_entries(inputs)
    if helper.inventory(work/'extracted-xacc/tree/install-xacc')!=xacc_before:
        raise ValueError('extracted baseline mutated')
    xacc_after=helper.inventory(work/'install-xacc')
    result={'core':core,'dependencies':dependencies,'xacc_unchanged':xacc_before==xacc_after,
            'phase':'before-core-install'}
    result['passed']=result['xacc_unchanged'] and all(v['unchanged'] for v in dependencies.values())
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cache',type=Path)
    parser.add_argument('--inputs',type=Path,default=Path('/inputs'))
    parser.add_argument('--work',type=Path,default=Path('/work'))
    args=parser.parse_args()
    raw=args.cache.read_bytes()
    result=selections(raw.decode())
    result['cache_sha256']=hashlib.sha256(raw).hexdigest()
    result['input_audit']=audit(args.inputs,args.work)
    print(json.dumps(result,sort_keys=True))
    if not result['input_audit']['passed']: raise SystemExit(1)
