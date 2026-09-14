import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import dependency_selection
import eigen_configure


class FlowTests(unittest.TestCase):
    def cmake(self):
        executable = os.environ.get('QB_CMAKE') or shutil.which('cmake')
        if not executable:
            if os.environ.get('QB_REQUIRE_CMAKE_TESTS') == '1':
                self.fail('CMake is required by QB_REQUIRE_CMAKE_TESTS=1')
            self.skipTest('CMake unavailable; CI requires script-only tests')
        return executable

    def test_transform_hash_guards_and_narrow_blocks(self):
        for module in (dependency_selection, eigen_configure):
            with self.assertRaises(ValueError):
                module.transform(module.OLD)
            with patch.object(module, 'SOURCE_SHA256', module.hashlib.sha256(module.OLD).hexdigest()):
                self.assertEqual(module.transform(module.OLD), module.NEW)
        self.assertNotIn(b'CMAKE_DISABLE_FIND_PACKAGE', dependency_selection.NEW)
        self.assertNotIn(b'rm -rf', eigen_configure.NEW)

    def test_scoped_override_and_nested_required_lookup(self):
        cmake = self.cmake()
        script = '''cmake_minimum_required(VERSION 3.20)
set(AMBIENT_CALLS 0)
set(NESTED_CALLS 0)
set(CPM_CALLS 0)
macro(find_package REQUESTED)
  if("${REQUESTED}" STREQUAL "Nested")
    if(NOT "${ARGN}" STREQUAL "REQUIRED")
      message(FATAL_ERROR "nested lookup must remain required")
    endif()
    if(DEFINED CMAKE_DISABLE_FIND_PACKAGE_Nested)
      message(FATAL_ERROR "global find suppression leaked")
    endif()
    math(EXPR NESTED_CALLS "${NESTED_CALLS}+1")
  else()
    math(EXPR AMBIENT_CALLS "${AMBIENT_CALLS}+1")
  endif()
  set(${REQUESTED}_FOUND TRUE)
endmacro()
macro(CPMAddPackage)
  math(EXPR CPM_CALLS "${CPM_CALLS}+1")
  find_package(Nested REQUIRED)
endmacro()
macro(probe NAME VERSION)
  set(arg_FIND_PACKAGE_NAME Ambient)
  set(arg_FIND_PACKAGE_VERSION "")
  set(arg_FIND_PACKAGE_ARGUMENTS "")
  set(Ambient_FOUND TRUE)
''' + dependency_selection.NEW.decode() + '''
  if(NOT Ambient_FOUND)
    CPMAddPackage(NAME ${NAME})
  endif()
endmacro()
set(CPM_Pinned_SOURCE "/verified source/with spaces")
probe(Pinned 1.0)
if(NOT AMBIENT_CALLS EQUAL 0 OR NOT CPM_CALLS EQUAL 1 OR NOT NESTED_CALLS EQUAL 1 OR NOT Nested_FOUND)
  message(FATAL_ERROR "explicit source did not bypass ambient lookup and retain nested lookup")
endif()
unset(CPM_Pinned_SOURCE)
probe(Pinned 1.0)
if(NOT AMBIENT_CALLS EQUAL 1 OR NOT CPM_CALLS EQUAL 1)
  message(FATAL_ERROR "missing override did not preserve original find")
endif()
set(CPM_Pinned_SOURCE "")
probe(Pinned 1.0)
if(NOT AMBIENT_CALLS EQUAL 2 OR NOT CPM_CALLS EQUAL 1)
  message(FATAL_ERROR "empty override did not preserve original find")
endif()
message(STATUS "PASS scoped source selection")
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'flow.cmake'
            path.write_text(script)
            result = subprocess.run([cmake, '-P', str(path)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS scoped source selection', result.stdout + result.stderr)

    def test_eigen_child_failure_is_fatal_and_build_directory_preserved(self):
        cmake = self.cmake()
        for failure in ('none', 'configure', 'install'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                calls = root / 'calls.jsonl'
                fake = root / 'fake-cmake'
                fake.write_text('#!' + sys.executable + '\n' + '''import json,pathlib,sys
args=sys.argv[1:]
with pathlib.Path(''' + repr(str(calls)) + ''').open('a') as out: out.write(json.dumps(args)+'\\n')
stage='configure' if args[0]=='-S' else 'install'
if stage=='configure': pathlib.Path(args[args.index('-B')+1]).mkdir(parents=True,exist_ok=True)
sys.exit(23 if stage==''' + repr(failure) + ''' else 0)
''')
                fake.chmod(0o755)
                script = root / 'eigen.cmake'
                build = root / 'build with spaces'
                script.write_text('cmake_minimum_required(VERSION 3.20)\n'
                    + f'set(CMAKE_COMMAND [=[{fake}]=])\nset(Eigen3_SOURCE_DIR [=[{root / "source with spaces"}]=])\n'
                    + f'set(Eigen3_BINARY_DIR [=[{build}]=])\nset(Eigen3_INSTALL_DIR [=[{root / "install with spaces"}]=])\n'
                    + eigen_configure.NEW.decode() + '\nmessage(STATUS "PASS Eigen child flow")\n')
                result = subprocess.run([cmake, '-P', str(script)], capture_output=True, text=True, timeout=20)
                recorded = [json.loads(line) for line in calls.read_text().splitlines()]
                self.assertEqual(recorded[0][0], '-S')
                self.assertEqual(recorded[0][recorded[0].index('-B')+1], str(build))
                for option in ('-DBUILD_TESTING=OFF', '-DEIGEN_BUILD_TESTING=OFF', '-DEIGEN_BUILD_DOC=OFF'):
                    self.assertIn(option, recorded[0])
                self.assertTrue(build.is_dir())
                if failure == 'none':
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(len(recorded), 2)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Eigen ' + failure + ' failed', result.stdout + result.stderr)
                    self.assertEqual(len(recorded), 1 if failure == 'configure' else 2)


if __name__ == '__main__':
    unittest.main()
