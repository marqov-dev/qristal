import difflib
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import dependency_path


class DependencyPathTests(unittest.TestCase):
    def fixture(self):
        return dependency_path.OLD + b'\n'.join(old for old, new in dependency_path.CALLS) + b'\n'

    def test_exact_transform_preserves_both_result_arguments(self):
        raw = self.fixture()
        with patch.object(dependency_path, 'SOURCE_SHA256', dependency_path.hashlib.sha256(raw).hexdigest()):
            transformed = dependency_path.transform(raw)
        self.assertIn(dependency_path.NEW, transformed)
        for old, new in dependency_path.CALLS:
            self.assertIn(new, transformed)
            self.assertNotIn(old, transformed)
        self.assertEqual(transformed.count(b' WAS_INSTALLED_BY_QRISTAL)'), 2)

    def test_changed_locked_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'locked dependency path source'):
            dependency_path.transform(self.fixture())

    def test_cmake_script_guard(self):
        cmake = os.environ.get('QB_CMAKE') or shutil.which('cmake')
        if not cmake:
            if os.environ.get('QB_REQUIRE_CMAKE_TESTS') == '1':
                self.fail('CMake is required by QB_REQUIRE_CMAKE_TESTS=1')
            self.skipTest('CMake unavailable; set QB_CMAKE for script-only verification')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prefix = root / 'install prefix'
            (prefix / 'inside space').mkdir(parents=True)
            sibling = root / 'install prefix-sibling'
            sibling.mkdir()
            outside = root / 'outside'
            outside.mkdir()
            script = 'cmake_minimum_required(VERSION 3.20)\n' + dependency_path.NEW.decode()
            script += f'set(CMAKE_INSTALL_PREFIX [=[{prefix}]=])\n'
            values = [('', False), ('${UNSET_PATH}', False), ('Pkg_DIR-NOTFOUND', False), ('NOTFOUND', False),
                      (str(prefix), True), (str(prefix / 'inside space'), True), (str(outside), False), (str(sibling), False)]
            for index, (value, expected) in enumerate(values):
                script += f'is_in_install_path("{value}" CHECK_RESULT)\n'
                script += f'if ({"NOT " if expected else ""}CHECK_RESULT)\n message(FATAL_ERROR "case {index} failed")\nendif()\n'
            script += 'set(arg_FIND_PACKAGE_NAME Pkg)\nunset(Pkg_DIR)\n' + dependency_path.CALLS[0][1].decode() + '\n'
            script += 'if(WAS_INSTALLED_BY_QRISTAL)\n message(FATAL_ERROR "unset package result")\nendif()\n'
            script += f'set(arg_FIND_PACKAGE_ADDITIONAL_RESULT_PATH_VAR EXTRA_PATH)\nset(EXTRA_PATH [=[{prefix / "inside space"}]=])\n'
            script += dependency_path.CALLS[1][1].decode() + '\n'
            script += 'if(NOT WAS_INSTALLED_BY_QRISTAL)\n message(FATAL_ERROR "additional path result")\nendif()\n'
            script += 'message(STATUS "PASS dependency path guard: empty/unset/NOTFOUND/equal/inside/outside/sibling/spaces/both call sites")\n'
            path = root / 'guard.cmake'
            path.write_text(script)
            result = subprocess.run([cmake, '-P', str(path)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS dependency path guard', result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
