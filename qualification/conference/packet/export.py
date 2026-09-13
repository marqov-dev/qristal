"""Export a self-contained conference evidence packet from an explicit allowlist."""
import argparse
import base64
import hashlib
import html
import json
from pathlib import Path
import subprocess
import zipfile

QUAL = Path(__file__).resolve().parents[2]
FILES = (
    "MAINTENANCE.md",
    "conference/CURRENT.md",
    "conference/readout-drift/readout-drift.png",
    "conference/readout-drift/provenance.json",
    "evidence/2026-09-12-readout-drift/result.json",
    "evidence/2026-09-12-readout-drift/analysis.json",
    "evidence/2026-09-12-readout-drift/manifest.json",
    "conference/README.md",
    "conference/WALKTHROUGH.md",
    "conference/cpu-gpu-correlations.png",
    "conference/observations.csv",
    "conference/provenance.json",
    "conference/readout-sweep/readout-sweep.png",
    "conference/readout-sweep/readout-sweep.csv",
    "conference/readout-sweep/figure-provenance.json",
    "conference/readout-mitigation/readout-mitigation.png",
    "conference/readout-mitigation/figure-provenance.json",
    "conference/readout-coverage/coverage.png",
    "conference/readout-coverage/provenance.json",
    "evidence/2026-09-12-readout-mitigation/analysis.json",
    "evidence/2026-09-12-readout-mitigation/result.json",
    "evidence/2026-09-12-readout-mitigation/manifest.json",
    "evidence/2026-09-12-readout-coverage/counts.json",
    "evidence/2026-09-12-readout-coverage/summary.json",
    "evidence/2026-09-12-readout-coverage/manifest.json",
)


def snapshot(root=QUAL):
    result = {}
    for name in FILES:
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("packet_source")
        raw = path.read_bytes()
        if len(raw) > 8*1024*1024:
            raise ValueError("packet_source_size")
        result[name] = raw
    return result


def document(files, revision):
    root = f"https://github.com/marqov-dev/qristal/tree/{revision}/qualification/"
    def figure(path, caption):
        uri = "data:image/png;base64,"+base64.b64encode(files[path]).decode()
        return f'<figure><img src="{uri}" alt="{html.escape(caption,quote=True)}"><figcaption>{html.escape(caption)}</figcaption></figure>'
    parts = ['''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Quantum Brilliance simulation research — Marqov</title>
<style>body{font:17px/1.6 system-ui,sans-serif;color:#172033;background:#f5f7fb;margin:0}
main{max-width:1080px;margin:auto;padding:48px 24px}h1{font-size:40px;line-height:1.2}
h2{margin-top:48px}a{color:#1555ae}figure{margin:24px 0;background:white;padding:16px;border-radius:12px}
img{width:100%;height:auto}figcaption,footer{font-size:14px;color:#4a5568}
.note{border-left:4px solid #d97706;padding:14px 20px;background:#fff7ed}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:12px;border-bottom:1px solid #ccd4e0}
@media print{body{background:white}main{padding:0}figure{break-inside:avoid}h2{break-after:avoid}}</style>
<main><p>MARQOV · RESEARCH NOTEBOOK</p><h1>Public simulation capabilities, reproducible evidence</h1>
<p>We rebuilt and tested a public Qristal CPU subset and qualified standalone CUDA-Q GPU alternatives.
The research connects scientific correctness, noise estimation and reliable execution.</p>
<p class="note">These are saved experiments, not hosted Marqov job results or QB hardware measurements.
The commercial QB Emulator and internal vQPU are outside this work. No partnership or endorsement is implied.</p>
<h2>Start here</h2>
<p>Show the noise and calibration experiments, compare CPU/GPU correlations, then
explain the packaging and maintenance work. These are useful public software
capabilities we can validate together, with hosted integration as a separate next step.</p>
<p>Full Decoder is an optional sequence-decoding research track. Its latest bounded
runs remain incomplete; separate scientific-research and engineering agents are
investigating it. It does not block these demonstrations or the platform release.</p>
<h2>1. The same circuit family across CPU and GPU methods</h2>
<p>QPP, Aer MPS and density matrix, plus CUDA-Q state-vector and tensor-network targets,
passed selected native fixtures. The GPU observations used NVIDIA A10G.
This compares correctness, not speed or maximum capacity.</p>''']
    parts.append(figure("conference/cpu-gpu-correlations.png","Native saved CPU/GPU observations. 16,384 shots per circuit; pointwise Wilson sampling intervals."))
    parts.append('<h2>2. Readout noise changes the observed distribution</h2><p>A 50-case native CPU sweep checked 25 asymmetric error settings with two seeds against analytic predictions. Maximum outcome residual: 0.493 percentage points.</p>')
    parts.append(figure("conference/readout-sweep/readout-sweep.png","Native Qristal/Aer readout sweep. The figure shows one seed; both remain in the accompanying CSV."))
    parts.append('<h2>3. Separate calibration improves held-out estimates</h2><p>Twenty-six native executions calibrated the readout matrix and tested separate samples. Mean absolute observable error fell by 95.64–96.03% in three selected settings. An unstable calibration was rejected; signed estimates were preserved.</p>')
    parts.append(figure("conference/readout-mitigation/readout-mitigation.png","Native CPU mitigation, restricted stationary q0 readout model. Approximate intervals include calibration uncertainty. This is not full SPAM or device calibration."))
    parts.append('<h2>4. A small error bar can miss calibration bias</h2><p>This separate synthetic study used 10,000 independently sampled calibration/measurement repetitions. Stationary coverage ranged from 94.3% to 96.5%; both deliberately stale scenarios had zero covered intervals in 1,000 repetitions per fixture. Sampling uncertainty does not include model mismatch.</p>')
    parts.append(figure("conference/readout-coverage/coverage.png","Synthetic multinomial sampling only — no Qristal or hardware execution. Wilson whiskers quantify Monte Carlo uncertainty in coverage; general coverage is not established."))
    parts.append('<h2>5. Fresh calibration restores the native estimates</h2><p>The predeclared 40-case Qristal/Aer experiment passed. Fresh calibration reduced aggregate error by approximately 95–98%. Stale calibration worsened two settings; with improved noise it produced 4.45 times the raw error.</p>')
    parts.append(figure("conference/readout-drift/readout-drift.png","Native Qristal/Aer observations: same held-out counts with stale and fresh calibration. Sampling intervals exclude systematic drift bias."))
    parts.append('''<h2>6. What is ready, and what remains</h2>
<table><tr><th>Evidence retained</th><th>Remaining boundary</th></tr>
<tr><td>Installed Core, selected Integrations and simplified Decoder fixtures</td><td>Full API/decoder coverage and supported public packaging</td></tr>
<tr><td>Private GPU candidate qualified on A10G</td><td>Original Core bridge, TNQVM, broader hardware and distribution</td></tr>
<tr><td>Bounded fault/recovery and exact cleanup after correction</td><td>Corrected-version soak, long-kernel interruption and hosted lifecycle</td></tr>
<tr><td>Native stationary mitigation and synthetic coverage study</td><td>Broader noise models, scaling and physical calibration</td></tr></table>
<h2>Partnership discussion</h2><p>Useful next conversations include public examples, maintenance boundaries,
upstream feedback and future hardware or commercial-plugin comparisons.</p>''')
    parts.append(f'<p><a href="{root}conference/CURRENT.md">Current conference summary</a> · <a href="{root}conference">Versioned research ledger</a> · <a href="{root}MAINTENANCE.md">Support and release gates</a> · <a href="https://app.marqov.ai/projects/776ca156-9051-4fcb-8aca-202e78a94cac/report">Marqov project report</a></p><footer>Packet source revision: {html.escape(revision)}. Embedded figures work offline. Linked repositories and Marqov require network access. Included evidence is a selected research subset, not the entire qualification archive.</footer></main></html>')
    return "\n".join(parts).encode()


def export(output):
    output.mkdir()
    files = snapshot()
    revision = subprocess.check_output(["git","rev-parse","HEAD"],cwd=QUAL).decode().strip()
    page = document(files,revision)
    manifest = dict(kind="conference-evidence-subset",revision=revision,
                    native_execution_performed_by_export=False,
                    files={name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()},
                    html_sha256=hashlib.sha256(page).hexdigest())
    manifest_raw=(json.dumps(manifest,indent=2)+"\n").encode()
    (output/"index.html").write_bytes(page)
    (output/"manifest.json").write_bytes(manifest_raw)
    with zipfile.ZipFile(output/"qb-research-packet.zip","w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.html",page)
        archive.writestr("manifest.json",manifest_raw)
        for name,raw in files.items():
            archive.writestr("evidence/"+name,raw)
    with zipfile.ZipFile(output/"qb-research-packet.zip") as archive:
        if archive.testzip() is not None:
            raise ValueError("archive_integrity")
        for name,digest in manifest["files"].items():
            if hashlib.sha256(archive.read("evidence/"+name)).hexdigest()!=digest:
                raise ValueError("archive_hash")
    print(json.dumps(dict(output=str(output),evidence_files=len(files),revision=revision)))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    export(parser.parse_args().output)
