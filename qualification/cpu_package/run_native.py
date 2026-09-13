"""Reuse the fixed CPU VM lifecycle for a bounded OCI build; no hosted deployment."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cpu_vm_lifecycle', HERE.parent / 'full_decoder/cloud/run.py')
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)
original_bootstrap = lifecycle.bootstrap


def bootstrap(url, digest):
    data = original_bootstrap(url, digest).decode()
    data = data.replace('qb-decoder-isolated-cpu-vm', 'qb-cpu-oci-native-v1')
    # Preserve captured payload modes; do not normalize the context after extraction.
    data = data.replace('chmod -R a+rX /work\n', '')
    data = data.replace('timeout 540 sh /work/install-toolchain.sh >/proof/toolchain.log 2>&1',
                        'timeout 240 sh -c "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker.io" >/proof/docker-install.log 2>&1')
    return data.encode()


if __name__ == '__main__':
    lifecycle.bootstrap = bootstrap
    sys.exit(lifecycle.main())
