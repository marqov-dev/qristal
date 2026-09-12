"""Visualize retained native drift observations without resampling."""
import argparse
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from check_evidence import check


def main(evidence, output):
    summary=check(evidence)
    output.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    labels=["Baseline\n20% / 10%","Increased\n25% / 10%","Increased\n35% / 10%",
            "Reversed\n10% / 20%","Improved\n5% / 2.5%"]
    colors={"raw":"#64748b","stale":"#d97706","fresh":"#2563eb"}
    for key in ("raw","stale","fresh"):
        axes[0].plot(range(5),[s["mae"][key] for s in summary["settings"]],
                     marker="o",color=colors[key],label=key.capitalize())
    axes[0].set(ylabel="Mean absolute observable error",title="Across six held-out circuits")
    bell=[r for r in summary["outcomes"] if r["fixture"]=="bell" and r["observable"]=="Z0Z1"]
    for key,offset in (("stale",-.07),("fresh",.07)):
        axes[1].errorbar([i+offset for i in range(5)],[r[key] for r in bell],
                         yerr=[1.96*r[key+"_se"] for r in bell],fmt="o",
                         capsize=4,color=colors[key],label=key.capitalize())
    axes[1].axhline(1,linestyle="--",color="#64748b",label="Ideal")
    axes[1].set(ylabel="Bell parity expectation",title="Calibration bias can exceed error bars")
    for ax in axes:
        ax.set_xticks(range(5),labels,fontsize=9)
        ax.grid(axis="y",alpha=.2)
        ax.legend()
    fig.suptitle("Fresh calibration tracks changes in simulated readout noise",fontsize=17,y=.97)
    fig.subplots_adjust(bottom=.26,top=.83,wspace=.30)
    fig.text(.08,.10,"Native Qristal/Aer CPU • 40 executions • 16,384 shots each • baseline calibration reused for stale estimates",fontsize=10)
    fig.text(.08,.055,"Left: Z0/Z0Z1 error averaged across six circuits. Right: approximate 95% sampling intervals; drift bias is not included.",fontsize=10)
    fig.text(.08,.015,"Independent q0 readout model, ideal preparation; not hardware, full SPAM or hosted execution.",fontsize=10)
    for suffix in ("png","svg"):
        fig.savefig(output/f"readout-drift.{suffix}",dpi=170)
    (output/"provenance.json").write_text(json.dumps(dict(
        result_sha256=hashlib.sha256((evidence/"result.json").read_bytes()).hexdigest(),
        plot_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        matplotlib=matplotlib.__version__,native_observations=True),indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("evidence",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    main(args.evidence,args.output)
