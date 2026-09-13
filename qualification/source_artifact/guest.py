"""Wrap the unchanged qualified guest; signed upload runs only on the host."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, '/proof/artifact-wrapper')
from archive import pack


def main():
    spec = importlib.util.spec_from_file_location('qualified_guest', '/work/guest.py')
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)
    original_emit = guest.emit

    def emit(report):
        # Preserve native report exactly inside the artifact; never weaken its checker.
        envelope = dict(report)
        try:
            if report.get('native_passed') is not True:
                raise ValueError('native failure; no reusable installation')
            logs = Path('/proof/retained-logs')
            logs.mkdir()
            for name in report['stages']:
                shutil.copyfile(Path('/proof') / (name + '.log'), logs / (name + '.log'))
            artifact = Path('/proof/output.tar.gz')
            identity = pack(artifact, report, {
                'install-xacc': '/work/install-xacc', 'consumer': '/proof/consumer',
                'consumer-output': '/proof/consumer-output', 'logs': logs})
            # The private URL is in a 0600 host-only curl config, not argv/env/logs.
            result = subprocess.run(['curl', '--config', '/proof/output-put.conf',
                '--silent', '--fail', '--max-time', '300', '--upload-file', str(artifact)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=315)
            if result.returncode:
                raise RuntimeError('output upload failed')
            envelope['output_artifact'] = identity
        except Exception as error:
            # Never serialize an exception that could contain signed request data.
            envelope['output_artifact_error'] = type(error).__name__
        finally:
            Path('/proof/output-put.conf').unlink(missing_ok=True)
        original_emit(envelope)
    guest.emit = emit
    guest.main()


if __name__ == '__main__':
    main()
