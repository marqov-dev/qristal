"""Source identity and acceptance checks for the bounded input-validation probe."""
import hashlib
from pathlib import Path
import re
import subprocess

SOURCE_FILES = (
    'src/quantum_decoder.cpp',
    'include/qristal/decoder/quantum_decoder.hpp',
    'include/qristal/decoder/register_validation.hpp',
    'include/qristal/decoder/result_accumulator.hpp',
    'tests/FullDecoderInputValidation.cpp',
)
TEST_NAMES = (
    'RejectsMissingOrWrongTypes', 'RejectsMalformedProbabilityTables',
    'AcceptsNormalizedTablesWithoutExecuting', 'RejectsRegistersAndUnsupportedOptions',
    'OwnsSharedBackendAndInvalidatesFailedInitialization', 'RejectsNullExplicitBackend',
)


def fingerprint(root):
    root = Path(root)
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def accepted(record, stdout):
    if record.get('exit_code') != 0 or record.get('harness_error'):
        return False
    if record.get('owned_container_absent') is not True:
        return False
    before, after = record.get('source_before'), record.get('source_after')
    if not before or set(before) != set(SOURCE_FILES) or before != after:
        return False
    output = stdout.decode('utf-8', errors='replace')
    return all(re.search(r'\[\s*OK\s*\]\s+FullDecoderInputValidation\.' + name + r'\s', output)
               for name in TEST_NAMES) and bool(re.search(r'\[\s*PASSED\s*\]\s+6 tests\.', output))


def cleanup_owned(name, run=subprocess.run):
    """Bounded cleanup of only this probe's exact name and ownership label."""
    query = ['docker', 'ps', '-aq', '--filter', f'name=^/{name}$',
             '--filter', f'label=qb.full-decoder={name}']
    def call(command):
        return run(command, capture_output=True, text=True, check=True, timeout=20).stdout
    try:
        for identity in call(query).split():
            call(['docker', 'rm', '-f', identity])
        return {'owned_container_absent': not call(query).strip()}
    except (OSError, subprocess.SubprocessError) as error:
        return {'owned_container_absent': False, 'cleanup_error': type(error).__name__}
