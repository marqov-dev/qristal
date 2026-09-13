#!/bin/sh
# Optional fixed stages; run only in the parent's isolated, networkless container.
set -eu
export PATH=/work/python-core/bin:/usr/local/bin:/usr/bin:/bin
export PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CMAKE_BUILD_PARALLEL_LEVEL=2
unset PYTHONPATH PYTHONHOME MPI_HOME

case "${1:-}" in
  antlr)
    python3.10 -c 'import sys,platform; assert sys.version_info[:2] == (3,10); assert sys.platform == "linux"; assert platform.machine() == "x86_64"'
    mkdir /work/antlr
    python3.10 /inputs/antlr/recipe.py prepare /inputs/antlr /work/antlr
    python3.10 -m venv /work/antlr/build-env
    /work/antlr/build-env/bin/python -m pip install --no-index --no-deps --no-cache-dir \
      /inputs/antlr/setuptools-59.6.0-py3-none-any.whl /inputs/antlr/wheel-0.37.1-py2.py3-none-any.whl
    /work/antlr/build-env/bin/python -m pip --version > /work/antlr/pip-version.txt
    /work/antlr/build-env/bin/python -c 'import sys,setuptools,wheel; print(sys.version); print(setuptools.__version__); print(wheel.__version__)' > /work/antlr/tools.txt
    cd /work/antlr/antlr4-python3-runtime-4.9.2
    if ! SOURCE_DATE_EPOCH=1609459200 /work/antlr/build-env/bin/python setup.py bdist_wheel \
      --dist-dir /work/antlr/wheels > /work/antlr/build.log 2>&1; then
      cat /work/antlr/build.log
      exit 1
    fi
    cat /work/antlr/build.log
    /work/antlr/build-env/bin/python /inputs/antlr/recipe.py verify \
      /work/antlr/wheels/antlr4_python3_runtime-4.9.2-py3-none-any.whl /work/antlr
    ;;
  python)
    python3.10 - <<'PY'
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0, '/inputs/antlr')
import recipe
root=Path('/inputs/python/wheels')
manifest=json.loads(Path('/inputs/python/core.json').read_text())
items=manifest['wheels']
assert manifest['schema']=='qb.python-artifact-inputs/v1' and len(items)==50
names={item['filename'] for item in items}
assert len(names)==50 and names=={p.name for p in root.iterdir()}
requirements=[]
for item in items:
    name=item['filename']
    assert Path(name).name==name and name.endswith('.whl')
    path=root/name
    assert not path.is_symlink() and path.is_file()
    assert path.stat().st_size==item['bytes']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
    requirements.append(str(path)+' --hash=sha256:'+item['sha256'])
antlr=Path('/work/antlr/wheels/antlr4_python3_runtime-4.9.2-py3-none-any.whl')
result=recipe.verify(antlr)
requirements.append(str(antlr)+' --hash=sha256:'+result['sha256'])
Path('/work/python-requirements.txt').write_text('\n'.join(requirements)+'\n')
print('Verified 50 acquired wheels and the newly built ANTLR wheel before installation')
PY
    python3.10 -m venv /work/python-core
    /work/python-core/bin/python -m pip install --no-index --no-deps --no-cache-dir \
      --only-binary=:all: --require-hashes -r /work/python-requirements.txt
    /work/python-core/bin/python -m pip check
    /work/python-core/bin/python -m pip freeze --all
    /work/python-core/bin/python -m pip --version
    ;;
  configure)
    test -f /work/source-core/CMakeLists.txt
    test -f /work/core-dependencies/overrides.cmake
    test -f /work/install-xacc/xacc-config.cmake
    if command -v nvq++ >/dev/null 2>&1; then
      echo 'Unexpected CUDA-Q compiler in CPU builder' >&2
      exit 2
    fi
    /work/python-core/bin/python -m pip check
    mkdir /work/build-core /work/install-core
    mkdir /work/install-core/python-site
    cmake --debug-find -C /work/core-dependencies/overrides.cmake \
      -S /work/source-core -B /work/build-core \
      -DCMAKE_INSTALL_PREFIX=/work/install-core -DCMAKE_INSTALL_LIBDIR=lib \
      -DCMAKE_BUILD_TYPE=Release '-DCMAKE_CXX_FLAGS_RELEASE=-O1 -DNDEBUG' \
      '-DCMAKE_C_FLAGS_RELEASE=-O1 -DNDEBUG' -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF \
      -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DCMAKE_Fortran_COMPILER=gfortran \
      -DCOMPILE_FOR_LOCAL_ARCH=OFF -DN_PROC=2 \
      -DCMAKE_DISABLE_FIND_PACKAGE_Eigen3:BOOL=TRUE -DCMAKE_DISABLE_FIND_PACKAGE_pybind11:BOOL=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_yaml-cpp:BOOL=TRUE -DCMAKE_DISABLE_FIND_PACKAGE_GTest:BOOL=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_nlohmann_json:BOOL=TRUE -DCMAKE_DISABLE_FIND_PACKAGE_range-v3:BOOL=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_autodiff:BOOL=TRUE -DCMAKE_DISABLE_FIND_PACKAGE_cereal:BOOL=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_args:BOOL=TRUE -DCMAKE_DISABLE_FIND_PACKAGE_cpr:BOOL=TRUE \
      -DCMAKE_DISABLE_FIND_PACKAGE_cppitertools:BOOL=TRUE \
      -DINSTALL_MISSING=CXX -DPython_EXECUTABLE=/work/python-core/bin/python \
      -DPython_FIND_VIRTUALENV=ONLY -DPYTHON_PACKAGES_PATH=/work/install-core/python-site \
      -DXACC_ROOT=/work/install-xacc -DXACC_DIR=/work/install-xacc \
      -DXACC_TAG=d1edaa7ae53edc7e335f46d33160f93d6020aaa3 \
      -DXACC_REPOSITORY=https://github.com/eclipse-xacc/xacc.git \
      -DWITH_MPI=OFF -DENABLE_MPI_IN_DEPS=OFF -DWITH_TNQVM=OFF -DWITH_TKET=OFF \
      -DWITH_CUDAQ=OFF -DWITH_PROFILING=OFF -DWITH_COVERAGE=OFF \
      -DBUILD_DOCS=OFF -DWITH_EXAMPLES=OFF -DBUILD_TESTS_WITHOUT_GPU=ON -DSUPPORT_EMULATOR_BUILD_ONLY=OFF \
      -DFETCHCONTENT_FULLY_DISCONNECTED=ON -DFETCHCONTENT_UPDATES_DISCONNECTED=ON \
      -DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF -DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF \
      '-DCMAKE_IGNORE_PREFIX_PATH=/opt/qb;/mnt/qb'
    ;;
  build)
    cmake --build /work/build-core --parallel 2 --target core pycore xacc-plugins
    ;;
  install)
    # XACC must be a fresh derivative: Core adds plugin links beneath it.
    cmake --install /work/build-core
    ;;
  *)
    echo 'Select exactly one stage: antlr | python | configure | build | install' >&2
    exit 2
    ;;
esac
