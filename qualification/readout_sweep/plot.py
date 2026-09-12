"""Render observed seed-42 readout outcomes; preserve all 50 cases in CSV."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

from demo import POINTS, SHOTS, probabilities, validate


def main(evidence, output):
    report = json.loads((evidence / "result.json").read_text())
    validate(report)
    output.mkdir(exist_ok=True)
    rows = []
    residuals = []
    grid = {}
    for record in report["records"]:
        opt = record["options"]
        p10, p01 = opt["readout"]["p10"], opt["readout"]["p01"]
        counts = record["counts"]
        expected = probabilities(p10, p01)
        residuals.extend(abs(counts.get(k, 0) / SHOTS - v) for k, v in expected.items())
        row = {
            "seed": opt["seed"],
            "p10": p10,
            "p01": p01,
            "shots": SHOTS,
            **{k: counts.get(k, 0) for k in ("00", "01", "10", "11")},
            "agreement": (counts.get("00", 0) + counts.get("11", 0)) / SHOTS,
            "imbalance": (counts.get("11", 0) - counts.get("00", 0)) / SHOTS,
            "expected_agreement": 1 - (p10 + p01) / 2,
            "expected_imbalance": (p10 - p01) / 2,
        }
        rows.append(row)
        if opt["seed"] == 42:
            grid[p10, p01] = row
    with (output / "readout-sweep.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "svg.hashsalt": "qb-readout-sweep-v1",
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(13.6, 7.0))
    fig.patch.set_facecolor("#f7f9fc")
    panels = [
        (
            "agreement",
            "Matching outcomes: P(00) + P(11)",
            "YlGnBu",
            {"vmin": 60, "vmax": 100},
        ),
        (
            "imbalance",
            "Outcome imbalance: P(11) − P(00)",
            "RdBu_r",
            {"norm": TwoSlopeNorm(vmin=-25, vcenter=0, vmax=25)},
        ),
    ]
    for ax, (key, title, cmap, options) in zip(axes, panels):
        values = [[100 * grid[p10, p01][key] for p10 in POINTS] for p01 in POINTS]
        im = ax.imshow(values, origin="lower", cmap=cmap, **options)
        ax.set_title(title, pad=16, fontsize=14, fontweight="bold")
        ax.set_xticks(range(5), [f"{v:.0%}" for v in POINTS])
        ax.set_yticks(range(5), [f"{v:.0%}" for v in POINTS])
        ax.set_xlabel("p10: report 1 when ideal outcome is 0", labelpad=12)
        ax.set_ylabel("p01: report 0 when ideal outcome is 1", labelpad=12)
        for y, row in enumerate(values):
            for x, value in enumerate(row):
                color = (
                    "white"
                    if (key == "agreement" and value > 87)
                    or (key == "imbalance" and abs(value) > 16)
                    else "#152238"
                )
                ax.text(
                    x,
                    y,
                    f"{value:.1f}",
                    ha="center",
                    va="center",
                    color=color,
                    fontsize=11,
                )
        ax.spines[:].set_visible(False)
        bar = fig.colorbar(im, ax=ax, shrink=0.76, pad=0.035)
        bar.set_label("percent" if key == "agreement" else "percentage points")
    fig.suptitle(
        "Bell-circuit readout: fewer matches, asymmetric outcomes",
        x=0.06,
        ha="left",
        fontsize=19,
        fontweight="bold",
        y=0.96,
    )
    fig.text(
        0.06,
        0.89,
        "Public Qristal / Aer CPU simulation · noise on qubit 0 only · 16,384 shots per circuit · plotted seed 42",
        fontsize=11,
    )
    fig.subplots_adjust(left=0.07, right=0.96, top=0.80, bottom=0.24, wspace=0.36)
    fig.text(
        0.06,
        0.115,
        "Analytic predictions: agreement = 1 − (p10 + p01)/2; imbalance = (p10 − p01)/2.",
        fontsize=11,
    )
    fig.text(
        0.06,
        0.065,
        f"50 cases across seeds 7 and 42 passed; largest outcome-probability residual = {100 * max(residuals):.3f} percentage points.\nDiscrete tested settings; shared seeds are not independent repetitions. Saved simulation results, not hardware or hosted jobs.",
        fontsize=10,
        color="#465366",
        linespacing=1.6,
    )
    fig.savefig(output / "readout-sweep.png", dpi=160, facecolor=fig.get_facecolor())
    fig.savefig(
        output / "readout-sweep.svg",
        facecolor=fig.get_facecolor(),
        metadata={"Date": None},
    )
    svg = output / "readout-sweep.svg"
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n"
    )
    plt.close(fig)
    (output / "figure-provenance.json").write_text(
        json.dumps(
            {
                "result_sha256": hashlib.sha256(
                    (evidence / "result.json").read_bytes()
                ).hexdigest(),
                "plot_source_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
                "plotted_seed": 42,
                "max_outcome_probability_residual": max(residuals),
                "files": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in output.iterdir()
                    if p.suffix in (".png", ".svg", ".csv")
                },
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.evidence, args.output)
