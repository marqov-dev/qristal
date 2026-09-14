import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('core_packaging_audit', HERE / 'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
fixture_module = audit.load('native_test_fixture', HERE.parent / 'core_native/test_result.py')


class AuditTests(unittest.TestCase):
    def fixture(self, root, mutate=None):
        # Synthetic known logs/commands only; no native code is built or run.
        report, protocol, log_archive = fixture_module.Tests().fixture(root)
        wheel_manifest = HERE.parent / 'evidence/2026-09-13-python-artifacts/core.json'
        wheel_bytes = wheel_manifest.read_bytes()
        entries = {'python/core.json': {'type': 'file', 'bytes': len(wheel_bytes), 'sha256': audit.sha(wheel_manifest)},
                   'python/wheels': {'type': 'directory', 'mode': 0o755}}
        for item in json.loads(wheel_bytes)['wheels']:
            entries['python/wheels/' + item['filename']] = dict(type='file', bytes=item['bytes'], sha256=item['sha256'])
        materials = root / 'material-manifest.json'
        materials.write_text(json.dumps({'schema': 'qb.core-material-manifest/v1', 'entries': entries}))
        protocol_data = json.loads(protocol.read_text())
        protocol_data['materials_sha256'] = audit.sha(materials)
        protocol_data.update(schema='qb.core-native-protocol/v1', operator_files={
            name: audit.sha(HERE.parent / name) for name in ('core_output/output.py', 'core_native/check_result.py')})
        protocol.write_text(json.dumps(protocol_data))
        report['protocol_sha256'] = audit.sha(protocol)
        report['materials_sha256'] = audit.sha(materials)
        roots = {name: root / name for name in audit.OUTPUT.SUCCESS_ROOTS}
        for path in roots.values():
            path.mkdir()
        with tarfile.open(log_archive) as stream:
            for member in stream:
                data = stream.extractfile(member).read()
                if member.name == 'logs/verify-inputs.log':
                    data = json.dumps({'verified': True, 'manifest_sha256': report['materials_sha256']}).encode()
                    report['stages']['verify-inputs']['log_sha256'] = hashlib.sha256(data).hexdigest()
                (root / member.name).write_bytes(data)
        payload = {'antlr/antlr4_python3_runtime-4.9.2-py3-none-any.whl': b'synthetic wheel',
                   'consumer/core.cpp': b'synthetic source', 'consumer-output/core': b'synthetic binary'}
        for name, data in payload.items():
            (root / name).write_bytes(data)
        report['retained_files'] = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
        if mutate:
            mutate(report)
        archive = root / 'core-output.tar.gz'
        identity = audit.OUTPUT.pack(archive, report, roots)
        report['output_artifact'] = identity
        native = root / 'recovered.json'
        native.write_text(json.dumps({'result': report}))
        return archive, protocol, native, materials

    def test_valid_evidence_yields_only_preparation_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit.audit(*self.fixture(Path(directory)))
            self.assertTrue(result['input_gate_passed'])
            for key in ('runtime_built', 'runtime_qualified', 'published', 'hosted'):
                self.assertFalse(result[key])
            self.assertEqual(len(result['required_python']['wheels']), 50)
            self.assertIn('QPP-only', result['scope'])

    def test_alternate_recovery_requires_and_preserves_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = self.fixture(root)
            baseline = audit.audit(*args)
            envelope = json.loads(args[2].read_text())
            envelope.update(schema='qb.core-recovered-report/v1', console_artifact_binding=False,
                            source='synthetic authenticated-object recovery fixture')
            args[2].write_text(json.dumps(envelope))
            with self.assertRaisesRegex(ValueError, 'requires its verification'):
                audit.audit(*args)
            report = envelope['result']
            identity = report['output_artifact']
            verification = audit.OUTPUT.verify(args[0], identity,
                {key: value for key, value in report.items() if key != 'output_artifact'})
            recovery = {'schema': 'qb.core-alternate-recovery/v1',
                        'authenticated_object_recovery': True, 'console_artifact_binding': False,
                        'identity': identity, 'archive_verification': verification,
                        'native_classification': baseline['native_classification']}
            sidecar = root / 'recovery.json'
            sidecar.write_text(json.dumps(recovery))
            result = audit.audit(*args, recovery_verification=sidecar)
            self.assertFalse(result['evidence_provenance']['console_artifact_binding'])
            self.assertEqual(result['evidence_provenance']['recovery_record_sha256'], audit.sha(sidecar))
            for replacement in (True, None):
                changed = dict(envelope, console_artifact_binding=replacement)
                args[2].write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    audit.audit(*args)
            args[2].write_text(json.dumps(envelope))
            recovery['identity'] = dict(identity, sha256='0' * 64)
            sidecar.write_text(json.dumps(recovery))
            with self.assertRaisesRegex(ValueError, 'verification mismatch'):
                audit.audit(*args, recovery_verification=sidecar)

    def test_failed_receipt_rejected_before_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            data = json.loads(args[2].read_text())
            data['result']['native_passed'] = False
            args[2].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'successful native evidence'):
                audit.audit(*args)

    def test_valid_archive_but_bad_native_command_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory), lambda report: report['stages']['consumer-python']['command'].append('--privileged'))
            with self.assertRaisesRegex(ValueError, 'native classification failed'):
                audit.audit(*args)

    def test_wrong_validator_version_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            data = json.loads(args[1].read_text())
            data['operator_files']['core_output/output.py'] = '0' * 64
            args[1].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'validator identity'):
                audit.audit(*args)

    def test_changed_or_missing_material_identity_rejected(self):
        for missing in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                args = self.fixture(Path(directory))
                if missing:
                    data = json.loads(args[1].read_text())
                    data.pop('materials_sha256')
                    args[1].write_text(json.dumps(data))
                else:
                    args[3].write_text(args[3].read_text() + '\n')
                with self.assertRaisesRegex(ValueError, 'material manifest identity'):
                    audit.audit(*args)

    def test_material_wheel_entry_type_hash_extras_and_metadata_binding(self):
        for mutation in ('hash', 'type', 'extra', 'missing', 'metadata'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                args = self.fixture(Path(directory))
                materials = json.loads(args[3].read_text())
                entries = materials['entries']
                name = next(name for name in entries if name.startswith('python/wheels/'))
                if mutation == 'hash':
                    entries[name]['sha256'] = '0' * 64
                elif mutation == 'type':
                    entries[name]['type'] = 'link'
                elif mutation == 'extra':
                    entries['python/wheels/extra.whl'] = entries[name]
                elif mutation == 'missing':
                    del entries[name]
                else:
                    entries['python/core.json']['bytes'] += 1
                args[3].write_text(json.dumps(materials))
                protocol = json.loads(args[1].read_text())
                protocol['materials_sha256'] = audit.sha(args[3])
                args[1].write_text(json.dumps(protocol))
                with self.assertRaisesRegex(ValueError, 'material (file identity|wheel)'):
                    audit.audit(*args)

    def test_duplicate_material_entries_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            args[3].write_text('{"schema":"qb.core-material-manifest/v1","entries":{},"entries":{}}')
            with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                audit.audit(*args)

    def test_tampered_archive_missing_receipt_and_duplicate_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.fixture(Path(directory))
            args[0].write_bytes(args[0].read_bytes() + b'changed')
            with self.assertRaises(ValueError):
                audit.audit(*args)
            args[2].unlink()
            with self.assertRaises(ValueError):
                audit.audit(*args)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            audit.parse('{"native_passed":false,"native_passed":true}')


if __name__ == '__main__':
    unittest.main()
