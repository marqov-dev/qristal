"""Local workload CLI only. Not a hosted Marqov execution/authority protocol."""
import argparse
from pathlib import Path
import sys
from adapter import SampleError, read_program, sample


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally echoes arbitrary user arguments in its diagnostics.
        self.exit(2, 'qristal_sample_failed:arguments\n')


def main():
    p = Parser()
    p.add_argument('--capabilities', action='store_true')
    p.add_argument('--qasm', type=Path)
    p.add_argument('--backend', default='qpp')
    p.add_argument('--qubits', type=int, default=2)
    p.add_argument('--shots', type=int, default=4096)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--readout-p10', type=float, default=0)
    p.add_argument('--readout-p01', type=float, default=0)
    a = p.parse_args()
    if a.capabilities:
        print(Path('/opt/qristal/capabilities.json').read_text())
        return 0
    try:
        data = read_program(a.qasm)
        payload = sample(data, backend=a.backend, qubits=a.qubits, shots=a.shots,
                         seed=a.seed, p10=a.readout_p10, p01=a.readout_p01)
        sys.stdout.buffer.write(payload + b'\n')
        return 0
    except SampleError as error:
        print('qristal_sample_failed:' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
