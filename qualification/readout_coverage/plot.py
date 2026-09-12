"""Plot retained synthetic coverage; no simulator or sampling."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/"evidence"/"2026-09-12-readout-coverage"/"summary.json"
OUTPUT=ROOT.parent/"conference"/"readout-coverage"
rows=json.loads(SOURCE.read_text())
fig,ax=plt.subplots(figsize=(11,5.8))
labels=["Stationary\n5% / 10%","Stationary\n20% / 10%","Stationary\n40% / 40%",
        "Stale: increased\n35% / 10%","Stale: improved\n5% / 2.5%"]
for j,(fixture,color) in enumerate((("zero","#2563eb"),("bell","#d97706"))):
    selected=[r for r in rows if r["fixture"]==fixture]
    y=[r["coverage"]*100 for r in selected]
    errors=[[100*(r["coverage"]-r["coverage_wilson95"][0]) for r in selected],
            [100*(r["coverage_wilson95"][1]-r["coverage"]) for r in selected]]
    errors=[[max(0,v) for v in side] for side in errors]
    x=[i+(j-.5)*.16 for i in range(5)]
    ax.errorbar(x,y,yerr=errors,fmt="o",capsize=4,color=color,label=fixture.capitalize())
ax.axhline(95,color="#64748b",linestyle="--",label="Nominal 95%")
ax.set(xticks=range(5),xticklabels=labels,ylim=(-4,104),ylabel="Intervals containing ideal parity (%)")
ax.set_title("Sampling intervals miss stale-calibration bias",loc="left",fontsize=17,pad=20)
ax.grid(axis="y",alpha=.2)
ax.legend(loc="center left")
fig.text(.09,.04,"Synthetic multinomial sampling • 1,000 independent repetitions per point • 16,384 shots per sample\nWhiskers: Wilson 95% Monte Carlo coverage intervals. Not Qristal execution or hardware measurements.",fontsize=10)
fig.subplots_adjust(bottom=.23,top=.87,left=.09,right=.98)
OUTPUT.mkdir(exist_ok=True)
for extension in ("png","svg"):
    fig.savefig(OUTPUT/f"coverage.{extension}",dpi=180)
(OUTPUT/"provenance.json").write_text(json.dumps(dict(input_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),plot_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),matplotlib=matplotlib.__version__,native_execution=False),indent=2)+"\n")
