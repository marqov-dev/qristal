"""Run inside qualified CPU container. Explicit Aer MPS/density methods, no fallback."""

import hashlib
import json
import sys

sys.path.insert(0, "/opt/qristal")
from adapter import quiet_native_engine
from fixtures import SHOTS, TOLERANCE, cases, check, qasm


def main():
    records = []
    for method in ("qpp", "matrix_product_state", "density_matrix"):
        for case in cases():
            source = qasm(case)
            with quiet_native_engine():
                import qristal.core as q

                s = q.session()
                s.acc = "qpp" if method == "qpp" else "aer"
                s.qn = case["qubits"]
                s.sn = SHOTS
                s.seed = 42
                s.noplacement = True
                s.nooptimise = True
                s.aer_omp_threads = 2
                s.remote_backend_database_path = "/opt/qristal/empty-backends.yaml"
                if method != "qpp":
                    s.aer_sim_type = method
                s.noise = False
                s.instring = source
                s.run()
                raw = s.results
                counts = {
                    "".join("1" if b else "0" for b in key): int(raw[key])
                    for key in raw
                }
            check(counts, case)
            records.append(
                {
                    "case": case["name"],
                    "requested_method": method,
                    "counts": counts,
                    "expected": case["expected"],
                    "program_sha256": hashlib.sha256(source.encode()).hexdigest(),
                }
            )
    print(
        json.dumps(
            {
                "scope": "local Qristal CPU methods; not TNQVM or GPU",
                "shots": SHOTS,
                "tolerance": TOLERANCE,
                "records": records,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
