#!/bin/sh
# Run only inside a disposable Linux CPython 3.10 container with --network none.
# /inputs (read-only): the three files pinned in inputs.json and this recipe.
# /output (empty, writable): complete retained build and wheel evidence.
set -eu
export PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONNOUSERSITE=1
export SOURCE_DATE_EPOCH=1609459200
python3.10 -c 'import sys,platform; assert sys.version_info[:2] == (3,10); assert sys.platform == "linux"; assert platform.python_implementation() == "CPython"'
python3.10 /inputs/recipe.py prepare /inputs /output
python3.10 -m venv /output/build-env
/output/build-env/bin/python -m pip install --no-index --no-deps --no-cache-dir \
    /inputs/setuptools-59.6.0-py3-none-any.whl /inputs/wheel-0.37.1-py2.py3-none-any.whl
/output/build-env/bin/python -m pip --version > /output/pip-version.txt
/output/build-env/bin/python -c 'import sys,setuptools,wheel; print(sys.version); print(setuptools.__version__); print(wheel.__version__)' > /output/tools.txt
cd /output/antlr4-python3-runtime-4.9.2
/output/build-env/bin/python setup.py bdist_wheel --dist-dir /output/wheels > /output/build.log 2>&1
/output/build-env/bin/python /inputs/recipe.py verify /output/wheels/antlr4_python3_runtime-4.9.2-py3-none-any.whl /output
