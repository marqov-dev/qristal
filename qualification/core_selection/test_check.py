import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('selection_check',Path(__file__).with_name('check.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class Tests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for name,package in c.PACKAGES.items():
            rows += [f'CPM_PACKAGE_{package}_SOURCE_DIR:INTERNAL=/work/core-dependencies/deps/{name}',
                     f'CPM_PACKAGE_{package}_BINARY_DIR:INTERNAL=/work/build-core/_deps/{name}-build']
        rows += [f'CMAKE_DISABLE_FIND_PACKAGE_{name}:BOOL=TRUE' for name in c.FIND_NAMES]
        rows += ['XACC_DIR:PATH=/work/install-xacc','XACC_ROOT:PATH=/work/install-xacc',
                 'CMAKE_HOME_DIRECTORY:INTERNAL=/work/source-core','CMAKE_INSTALL_PREFIX:PATH=/work/install-core']
        return '\n'.join(rows)
    def test_all_selections(self):
        result=c.selections(self.fixture())
        self.assertEqual(len(result['cpm_sources']),11)
        self.assertFalse(result['target_linkage_verified'])
    def test_override_alone_is_insufficient(self):
        raw=self.fixture().replace('CPM_PACKAGE_Eigen3_SOURCE_DIR:INTERNAL','CPM_Eigen3_SOURCE:PATH')
        with self.assertRaises(ValueError):c.selections(raw)
    def test_wrong_source_and_case(self):
        for source in ['/usr/include/eigen3','/work/core-dependencies/deps/eigen3/../cpr']:
            with self.assertRaises(ValueError):c.selections(self.fixture().replace('/work/core-dependencies/deps/eigen3',source))
        with self.assertRaises(ValueError):c.selections(self.fixture().replace('CPM_PACKAGE_Eigen3','CPM_PACKAGE_eigen3'))
    def test_binary_escape(self):
        for path in ['/tmp/build','/work/build-core/../outside','/work/build-core']:
            with self.assertRaises(ValueError):c.selections(self.fixture().replace('/work/build-core/_deps/cpr-build',path))
    def test_find_gate_and_xacc(self):
        with self.assertRaises(ValueError):c.selections(self.fixture().replace('CMAKE_DISABLE_FIND_PACKAGE_GTest:BOOL=TRUE','CMAKE_DISABLE_FIND_PACKAGE_GTest:BOOL=FALSE'))
        with self.assertRaises(ValueError):c.selections(self.fixture().replace('XACC_DIR:PATH=/work/install-xacc','XACC_DIR:PATH=/opt/qb'))
    def test_duplicate_cache_key(self):
        with self.assertRaises(ValueError):c.selections(self.fixture()+'\nXACC_DIR:PATH=/work/install-xacc')

class AuditTests(unittest.TestCase):
    def fixture(self,root):
        inputs,work=root/'inputs',root/'work'
        for base in (inputs/'core',work/'source-core'):
            (base/'include/qristal/core').mkdir(parents=True)
            (base/'include/qristal/core/cmake_variables.hpp').write_text('generated')
            (base/'CMakeLists.txt').write_text('source')
        for name in c.PACKAGES:
            for base in (inputs/'core-dependencies/deps'/name,work/'core-dependencies/deps'/name):
                base.mkdir(parents=True);(base/'input').write_text(name)
        for base in (work/'extracted-xacc/tree/install-xacc',work/'install-xacc'):
            base.mkdir(parents=True);(base/'library').write_bytes(b'original')
        baseline_inputs(inputs,c.native_helpers().inventory(work/'extracted-xacc/tree/install-xacc'))
        return inputs,work
    def test_only_generated_header_change(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            inputs,work=self.fixture(Path(tmp))
            (work/'source-core/include/qristal/core/cmake_variables.hpp').write_text('new generated header')
            self.assertTrue(c.audit(inputs,work)['passed'])
    def test_dependency_mutation_reported_and_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            inputs,work=self.fixture(Path(tmp))
            (work/'core-dependencies/deps/cpr/input').write_text('changed')
            result=c.audit(inputs,work)
            self.assertFalse(result['passed'])
            self.assertIn('input',result['dependencies']['cpr']['changes'])
    def test_xacc_mutation_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            inputs,work=self.fixture(Path(tmp))
            (work/'install-xacc/library').write_bytes(b'changed')
            self.assertFalse(c.audit(inputs,work)['passed'])
    def test_unexpected_core_manifest_not_ignored(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            inputs,work=self.fixture(Path(tmp))
            (work/'source-core/material-manifest.json').write_text('{}')
            with self.assertRaises(ValueError):c.audit(inputs,work)


def baseline_inputs(inputs,entries):
    import tarfile,io,json,hashlib
    root=inputs/'xacc';root.mkdir(parents=True)
    converted={}
    for name,entry in entries.items():
        info=dict(entry)
        if info['type']=='link':info={'type':'symlink','target':info['target'],'mode':0o777}
        elif info['type']=='file':info['size']=info.pop('bytes')
        converted['install-xacc/'+name]=info
    raw=json.dumps({'schema':'qb.source-artifact/v1','entries':converted}).encode()
    path=root/'archive.tar.gz'
    with tarfile.open(path,'w:gz') as tar:
        member=tarfile.TarInfo('receipt.json');member.size=len(raw);tar.addfile(member,io.BytesIO(raw))
    (root/'recovered.json').write_text(json.dumps({'output_artifact':{
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,
        'receipt_sha256':hashlib.sha256(raw).hexdigest()}}))
