#!/bin/sh
# Execute only during a separately authorized linux/amd64 image build.
set -eu
export PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
python3.10 -c 'import sys,platform; assert sys.version_info[:2] == (3,10); assert sys.platform == "linux"; assert platform.machine() == "x86_64"'
python3.10 -m venv /work/python-core
/work/python-core/bin/python -m pip install --no-index --no-deps --no-cache-dir --only-binary=:all: --require-hashes -r /inputs/requirements.txt
/work/python-core/bin/python -m pip check
/work/python-core/bin/python -m pip freeze --all > /opt/qristal/python-packages.txt
