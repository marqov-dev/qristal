"""Render retained native observations; no simulator or cloud execution."""

from pathlib import Path
import csv
import hashlib
import json
import math
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
cpu_path = ROOT / "evidence/2026-09-11-cpu-methods/cpu.stdout"
gpu_path = ROOT / "evidence/2026-09-11-gpu-feasibility/result.json"
cpu = json.loads(cpu_path.read_text())
gpu = json.loads(gpu_path.read_text())
labels = {
    "qpp": "Qristal QPP · CPU",
    "matrix_product_state": "Aer MPS · CPU",
    "density_matrix": "Aer density matrix · CPU",
}
rows = []
for record in cpu["records"]:
    if record["case"] in ("bell", "ghz8"):
        rows.append((labels[record["requested_method"]], record))
for result in gpu["results"]:
    for record in result["records"]:
        if record["case"] in ("bell", "ghz8"):
            rows.append(("CUDA-Q " + str(result["target"]) + " · A10G", record))
export = []
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
for ax, case, title in zip(
    axes, ("bell", "ghz8"), ("Bell · 2 qubits", "GHZ · 8 qubits")
):
    selected = [(label, r) for label, r in rows if r["case"] == case]
    for i, (label, r) in enumerate(selected):
        n = sum(r["counts"].values())
        assert n == 16384
        bits = "00" if case == "bell" else "00000000"
        assert set(r["counts"]) <= {bits, "1" * len(bits)}
        k = r["counts"].get(bits, 0)
        estimate = k / n
        z = 1.95996398454
        center = (estimate + z * z / (2 * n)) / (1 + z * z / n)
        half = (
            z
            * math.sqrt(estimate * (1 - estimate) / n + z * z / (4 * n * n))
            / (1 + z * z / n)
        )
        low, high = center - half, center + half
        ax.errorbar(
            estimate * 100,
            i,
            xerr=[[(estimate - low) * 100], [(high - estimate) * 100]],
            fmt="o",
            color="#147d92" if i < 3 else "#a54cd3",
            capsize=4,
            markersize=7,
        )
        export.append(
            dict(
                method=label,
                case=case,
                zero_count=k,
                shots=n,
                probability=estimate,
                wilson95_low=low,
                wilson95_high=high,
                program_sha256=r["program_sha256"],
            )
        )
    ax.axvline(50, color="#777777", linestyle="--", linewidth=1)
    ax.set_title(title, fontsize=15, pad=15)
    ax.set_xlim(48.5, 51.5)
    ax.set_xlabel("All-zero outcome (%)")
    ax.set_yticks(range(len(selected)), [label for label, _ in selected])
    ax.grid(axis="x", alpha=0.15)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].invert_yaxis()
fig.suptitle("One circuit family, five simulation methods", fontsize=20, x=0.53)
fig.text(
    0.53,
    0.025,
    "Saved native simulations · 16,384 shots/circuit · pointwise Wilson 95% intervals\nIdeal probability: 50% · correctness comparison, not a speed or capacity benchmark",
    ha="center",
    fontsize=10,
    color="#444444",
)
fig.tight_layout(rect=(0, 0.10, 1, 0.91))
fig.savefig(OUT / "cpu-gpu-correlations.png", dpi=180)
fig.savefig(OUT / "cpu-gpu-correlations.svg")
with (OUT / "observations.csv").open("w") as f:
    writer = csv.DictWriter(f, fieldnames=list(export[0]))
    writer.writeheader()
    writer.writerows(export)
(OUT / "provenance.json").write_text(
    json.dumps(
        {
            "source_commit": "fe745fecd2b19f7100996cbffeb4ec30d1ed08c6",
            "inputs": {
                str(path.relative_to(ROOT.parent)): hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (cpu_path, gpu_path)
            },
            "scope": "Replot of retained observations, not new runs. Marginal sampling intervals, not independent hardware repetitions or simultaneous coverage.",
        },
        indent=2,
    )
    + "\n"
)
