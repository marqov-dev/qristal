"""Run one fixed fresh-source CPU VM using the existing recovery/cleanup lifecycle."""
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('source_vm_lifecycle', HERE.parent / 'full_decoder/cloud/run.py')
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)
original_bootstrap = lifecycle.bootstrap


class SourceSupervisor(lifecycle.Supervisor):
    @staticmethod
    def initialize(directory, plan, userdata, *, seconds=1200, cleanup_seconds=300):
        return lifecycle.SupervisorBase.initialize(directory, plan, userdata,
                                                   seconds=3600, cleanup_seconds=300)


def bootstrap(url, digest):
    original = original_bootstrap(url, digest).decode()
    if original.count('shutdown -h +20') != 1 or original.count('timeout 540 sh /work/install-toolchain.sh >/proof/toolchain.log 2>&1') != 1:
        raise ValueError('lifecycle bootstrap changed')
    return original.replace('shutdown -h +20', 'shutdown -h +60').replace(
        'qb-decoder-isolated-cpu-vm','qb-xacc-fresh-source-v1').replace(
        'chmod -R a+rX /work\n','').replace(
        'timeout 540 sh /work/install-toolchain.sh >/proof/toolchain.log 2>&1',
        'timeout 240 sh -c "apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker.io" >/proof/docker-install.log 2>&1').encode()


if __name__ == '__main__':
    lifecycle.SupervisorBase = lifecycle.Supervisor
    lifecycle.Supervisor = SourceSupervisor
    lifecycle.bootstrap = bootstrap
    sys.exit(lifecycle.main())
