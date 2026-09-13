import contextlib
import copy
import io
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import guest
import pack_native
import run_native
import stage


def load_local(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NativeTests(unittest.TestCase):
    def test_bootstrap_preserves_modes_and_fixed_deadline(self):
        script = run_native.bootstrap('https://example.test/artifact', 'a' * 64)
        self.assertEqual(subprocess.run(['bash', '-n'], input=script, capture_output=True).returncode, 0)
        self.assertIn(b'shutdown -h +20', script)
        self.assertIn(b'timeout 240', script)
        self.assertNotIn(b'chmod -R', script)
        self.assertNotIn(b'install-toolchain', script)
        for url in ("https://example.test/'", 'https://example.test/\n'):
            with self.assertRaises(ValueError):
                run_native.bootstrap(url, 'a' * 64)

    def test_report_recovers_with_existing_protocol(self):
        console = load_local('cpu_test_console', Path(__file__).resolve().parents[1] / 'gpu_package/console.py')
        data = {'kind':'qb-cpu-oci-native-v1','native_passed':True,'tests':{'image':'fixture'}}
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            guest.emit(data)
        recovered, _, _ = console.recover(output.getvalue())
        self.assertEqual(recovered, data)

    def test_archive_contains_only_context_and_named_harness(self):
        import tarfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source'
            source.mkdir()
            (source / 'fixture').write_text('public fixture')
            context = root / 'context'
            with patch.dict(stage.INPUTS, {'fixture':'opt/fixture'}, clear=True):
                stage.stage(source, stage.capture(source), context)
            artifact = root / 'artifact'
            pack_native.pack(context, artifact)
            with tarfile.open(artifact / 'cpu.tar.gz') as archive:
                roots = {p.name.split('/')[0] for p in archive.getmembers()}
            self.assertEqual(roots, {'context','stage.py','guest.py','qristal','manifest.json'})
            record = json.loads((artifact / 'archive.json').read_text())
            self.assertEqual(record['sha256'], stage.sha(artifact / 'cpu.tar.gz'))
            with self.assertRaises(ValueError):
                pack_native.pack(context, context / 'bad')

    def test_report_failure_is_not_native_success(self):
        check_native = load_local('cpu_test_checker', stage.HERE / 'check_native.py')
        self.assertFalse(check_native.verify({'kind':'qb-cpu-oci-native-v1','error':'image_build_failed'}, {})['native_passed'])
        self.assertFalse(check_native.verify({'kind':'qb-cpu-oci-native-v1','bootstrap_exit_code':1}, {})['native_passed'])

    def test_native_identity_and_negative_exit_binding(self):
        check_native = load_local('cpu_test_checker', stage.HERE / 'check_native.py')
        image = 'sha256:' + 'a' * 64
        files = {'stage.py':stage.HERE / 'stage.py', 'guest.py':stage.HERE / 'guest.py',
                 'qristal/qualification/runtime/test_image.py':stage.HERE.parent / 'runtime/test_image.py'}
        manifest = {'schema':'marqov.cpu-native-input/v1','context_sha256':'b' * 64,'files':{n:stage.sha(p) for n,p in files.items()}}
        names = ['capabilities','core','noise','integration','decoder','bell','noisy-bell','reject-shots','reject-gpu','isolation']
        report = {'kind':'qb-cpu-oci-native-v1','manifest':manifest,'context_sha256':manifest['context_sha256'],
                  'image_config':{'User':'65532:65532','Entrypoint':['python3','/opt/qristal/runtime.py'],'Cmd':['--capabilities'],'WorkingDir':'/tmp'},
                  'published':False,'native_passed':True,'image':image,'image_inspected_id':image,
                  'stages':{'build':{'exit':0},'checks':{'exit':0}},
                  'tests':{'image':image,'no_host_mounts':True,'tests':[
                      {'name':n,'exit':2 if n.startswith('reject-') else 0,'command':check_native.expected_command(n,'marqov-runtime-test-0123456789',image)} for n in names]}}
        self.assertTrue(check_native.verify(report,manifest)['native_passed'])
        bad = copy.deepcopy(report)
        bad['tests']['tests'][-2]['exit'] = 0
        with self.assertRaises(ValueError):
            check_native.verify(bad,manifest)
        bad = copy.deepcopy(report)
        bad['image_inspected_id'] = 'sha256:' + 'c' * 64
        with self.assertRaises(ValueError):
            check_native.verify(bad,manifest)
        bad = copy.deepcopy(report)
        bad['tests']['tests'][0]['command'].insert(2,'--privileged')
        with self.assertRaises(ValueError):
            check_native.verify(bad,manifest)
        bad = copy.deepcopy(report)
        bad['image_config']['User'] = '0'
        with self.assertRaises(ValueError):
            check_native.verify(bad,manifest)

    def test_retained_native_evidence_and_cleanup(self):
        checker = load_local('cpu_retained_checker', stage.HERE / 'check_evidence.py')
        evidence = stage.HERE.parent / 'evidence/2026-09-13-cpu-oci'
        result = checker.verify(evidence)
        self.assertTrue(result['native_passed'])
        self.assertTrue(result['cleanup_verified'])
        self.assertFalse(result['gpu_backend_rejection_verified'])
