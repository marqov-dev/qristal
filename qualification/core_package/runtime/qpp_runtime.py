"""QPP-only local CLI; no hosted authority or network backend selection."""
import runtime
from adapter import SampleError, sample as shared_sample


def qpp_sample(data, *, backend='qpp', qubits=2, shots=4096, seed=42, p10=0.0, p01=0.0):
    # Fail before entering/importing native code, even if extra plugins exist.
    if backend != 'qpp':
        raise SampleError('backend')
    if p10 != 0 or p01 != 0:
        raise SampleError('noise_backend')
    return shared_sample(data, backend=backend, qubits=qubits, shots=shots,
                         seed=seed, p10=p10, p01=p01)


def main():
    runtime.sample = qpp_sample
    return runtime.main()


if __name__ == '__main__':
    raise SystemExit(main())
