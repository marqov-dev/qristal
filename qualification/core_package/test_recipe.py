"""Offline contract tests; no simulator, package manager or container execution."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import recipe
sys.path.insert(0, str(HERE.parent / 'runtime'))
spec = importlib.util.spec_from_file_location('qpp_cli', HERE / 'runtime/qpp_runtime.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class RecipeTests(unittest.TestCase):
    def test_rejects_other_backend_and_noise_without_native_execution(self):
        with patch.object(cli, 'shared_sample') as engine:
            for opts in ({'backend': 'aer'}, {'backend': 'tnqvm'}, {'p10': .1}, {'p01': .1}):
                with self.assertRaises(cli.SampleError):
                    cli.qpp_sample(b'input', **opts)
            engine.assert_not_called()

    def test_delegates_qpp_to_existing_adapter(self):
        with patch.object(cli, 'shared_sample', return_value=b'result') as engine:
            self.assertEqual(cli.qpp_sample(b'input'), b'result')
            self.assertEqual(engine.call_args.kwargs['backend'], 'qpp')

    def test_recipe_preserves_false_binding_and_offline_wheel_hashes(self):
        plan = {'bindings': {'archive_sha256': 'a' * 64},
                'evidence_provenance': {'console_artifact_binding': False},
                'required_python': {'wheels': [{'filename': 'example.whl', 'sha256': 'b' * 64}],
                                    'antlr': {'archive_path': 'antlr/antlr.whl', 'sha256': 'c' * 64}}}
        with tempfile.TemporaryDirectory() as d:
            result = recipe.attach(Path(d), plan)
            self.assertFalse(result['build_ready'])
            self.assertFalse(result['evidence_provenance']['console_artifact_binding'])
            self.assertIn('--hash=sha256:' + 'b' * 64, (Path(d)/'runtime/requirements.txt').read_text())
            cap = json.loads((Path(d)/'runtime/capabilities.json').read_text())
            self.assertEqual(cap['backends'], ['qpp'])
            self.assertEqual(cap['noise_cli'], [])
            self.assertIn('adapter.py', result['assets_sha256'])


if __name__ == '__main__':
    unittest.main()
