"""Local integrity experiment only. No hosted delivery or provenance authority.

Parsing/recomputation belongs inside the bounded credential-free workload. Policy
values here are supplied by the test caller, not authenticated by this module.
"""
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

from adapter import read_program, validate_options
from candidate import unique_object, reject_constant, validate_candidate
from program_guard import prepare


class BindingError(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def closed_json(raw, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise ValueError()
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def policy_check(policy, lock):
    if type(policy) is not dict or set(policy) != {'image_sha256','dependency_lock_sha256'}:
        raise ValueError()
    for value in policy.values():
        if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError()
    if type(lock) is not bytes or not 0 < len(lock) <= 65536 or digest(lock) != policy['dependency_lock_sha256']:
        raise ValueError()


def assemble(program, options, lock, *, backend, policy):
    """Return fixed-name files and a local manifest. No paths or credentials accepted."""
    try:
        policy_check(policy, lock)
        settings=closed_json(options,1024)
        if type(settings) is not dict or set(settings) != {'qubits','shots','seed'}:
            raise ValueError()
        validate_options(backend,settings['qubits'],settings['shots'],settings['seed'],0,0)
        prepared=prepare(program,settings['qubits'])
        files={'original.qasm':program,'canonical.qasm':prepared.canonical,
               'options.json':options,'dependencies.lock':lock}
        manifest={'local_only':True,'backend':backend,'settings':settings,
                  'artifacts':{name:digest(raw) for name,raw in files.items()},
                  'logical_bits':[f'q[{i}]' for i in range(settings['qubits'])],
                  'policy':dict(policy),'parser':{'qiskit_terra':version('qiskit-terra'),
                  'guard_sha256':digest(Path(__file__).with_name('program_guard.py').read_bytes())}}
        return files,json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
    except Exception:
        raise BindingError('local_binding_rejected') from None


def verify(directory, expected_manifest, *, backend, policy):
    """Recompute preparation from staged bytes and compare with caller-retained facts.

    The directory must be a caller-owned isolated fixture directory. This function
    is not a race-proof shared-filesystem or cross-tenant delivery mechanism.
    """
    try:
        manifest=closed_json(expected_manifest,8192)
        names={'original.qasm','canonical.qasm','options.json','dependencies.lock'}
        directory=Path(directory)
        if {p.name for p in directory.iterdir()} != names:
            raise ValueError()
        files={name:read_program(directory/name) for name in names}
        rebuilt,raw=assemble(files['original.qasm'],files['options.json'],files['dependencies.lock'],
                             backend=backend,policy=policy)
        if rebuilt != files or json.dumps(manifest,sort_keys=True,separators=(',',':')).encode() != raw:
            raise ValueError()
        # Return private byte snapshots; execution must use these bytes, not reread paths.
        return files,manifest
    except Exception:
        raise BindingError('local_binding_rejected') from None


def validate_prepared_result(directory, expected_manifest, stdout, *, returncode, backend, policy):
    files,manifest=verify(directory,expected_manifest,backend=backend,policy=policy)
    try:
        settings=manifest['settings']
        result=validate_candidate(stdout,returncode=returncode,program=files['canonical.qasm'],
                                  backend=backend,qubits=settings['qubits'],shots=settings['shots'])
        if list(result.logical_bits) != manifest['logical_bits']:
            raise ValueError()
        return result
    except Exception:
        raise BindingError('local_binding_rejected') from None
