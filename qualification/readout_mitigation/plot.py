"""Pointwise held-out parity comparison, with calibration uncertainty retained."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from demo import FIXTURES, POINTS, analyze


def main(evidence, output):
    report = json.loads((evidence / "result.json").read_text())
    summary = analyze(report)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.hashsalt": "qb-independent-mitigation-v1"})
    fig, axes = plt.subplots(1, 3, figsize=(14.4, 7.1), sharey=True)
    fig.patch.set_facecolor("#f7f9fc")
    names = list(FIXTURES)
    labels = ["00", "10", "01", "11", "H(q0)", "Bell"]
    colors = ("#2879b9", "#da7d21")
    for setting, ax in enumerate(axes):
        values = {r["fixture"]: r for r in summary["outcomes"]
                  if r["setting"] == setting and r["observable"] == "Z0Z1"}
        for key, offset, color, marker, label in (
            ("raw", -.10, colors[0], "o", "Observed"),
            ("corrected", .10, colors[1], "D", "Corrected"),
        ):
            ax.errorbar([i + offset for i in range(6)], [values[n][key] for n in names],
                        yerr=[1.96 * values[n][key + "_se"] for n in names],
                        fmt=marker, color=color, markersize=5, capsize=3,
                        elinewidth=1.2, linestyle="none", label=label)
        ax.plot(range(6), [values[n]["ideal"] for n in names], linestyle="none",
                marker="_", markersize=19, markeredgewidth=2, color="#263b4c",
                label="Ideal target")
        ax.set_xticks(range(6), labels)
        ax.set_ylim(-1.25, 1.25)
        ax.set_xlim(-.45, 5.45)
        ax.set_yticks([-1, -.5, 0, .5, 1])
        ax.grid(axis="y", alpha=.18)
        ax.spines[["top", "right"]].set_visible(False)
        a, b = POINTS[setting]
        ax.set_title(f"p10 = {a:.0%}   ·   p01 = {b:.0%}", fontweight="bold", pad=15)
        ax.set_xlabel("Held-out circuit", labelpad=10)
        metrics = summary["settings"][setting]
        raw = metrics["raw_mean_absolute_observable_error"]
        corrected = metrics["corrected_mean_absolute_observable_error"]
        ax.text(.5, -.30, f"Mean observable error: {raw:.3f} → {corrected:.3f}",
                transform=ax.transAxes, ha="center", fontsize=10)
    axes[0].set_ylabel("Parity expectation ⟨Z0 Z1⟩")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(.96, .895),
               ncol=3, frameon=False, fontsize=10)
    fig.suptitle("Readout correction tested on separate samples",
                 x=.065, ha="left", y=.965, fontsize=21, fontweight="bold")
    fig.text(.065, .902, "Public Qristal / Aer CPU · 16,384 shots per circuit · noise on q0 only",
             fontsize=11)
    fig.subplots_adjust(left=.065, right=.97, top=.78, bottom=.32, wspace=.15)
    fig.text(.065, .13,
             "Calibration uses separate prepared-zero/one samples. Error bars: pointwise approximate 95% intervals, including calibration uncertainty.",
             fontsize=10)
    fig.text(.065, .077,
             "Mean error averages Z0 and Z0Z1 over all six held-out circuits. Signed estimates are not clipped; the near-singular control is rejected.",
             fontsize=10)
    fig.text(.065, .029, "Saved simulations under a stationary readout model, not hardware calibration or hosted Marqov jobs.",
             fontsize=10, color="#465366")
    fig.savefig(output / "readout-mitigation.png", dpi=160, facecolor=fig.get_facecolor())
    fig.savefig(output / "readout-mitigation.svg", facecolor=fig.get_facecolor(),
                metadata={"Date": None})
    svg = output / "readout-mitigation.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    (output / "figure-provenance.json").write_text(json.dumps({
        "result_sha256": hashlib.sha256((evidence / "result.json").read_bytes()).hexdigest(),
        "plot_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "intervals": "pointwise normal delta method including calibration variance",
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in output.iterdir() if p.suffix in (".png", ".svg")},
    }, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.evidence, args.output)
