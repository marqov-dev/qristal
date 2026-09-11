# Bell-circuit readout sweep

Native CPU experiment, 11 September 2026: **50 cases passed**, each with 16,384
shots. We reused the existing qualified public Qristal/Aer image and bounded
readout harness. No image was rebuilt, no dependency was installed and no cloud
job was submitted for this experiment. The owned local container was removed.

The executed script declares a 5×5 grid of `p10,p01` values: 0, .05, .10, .20,
.40, repeated for seeds 7 and 42. `p10` means report 1 given ideal 0; `p01` means
report 0 given ideal 1. Noise acts on qubit zero only. Bit strings list q[0] first.

For the fixed Bell circuit, independently derived outcome probabilities are:

| Outcome | Probability |
|---|---|
| 00 | (1 − p10) / 2 |
| 10 | p10 / 2 |
| 01 | p01 / 2 |
| 11 | (1 − p01) / 2 |

Consequently, matching outcomes have probability `1 − (p10+p01)/2`, while
`P(11)−P(00)=(p10−p01)/2`. The executed validator requires every probability
within a predeclared 2.5 percentage-point tolerance, exact absence for zero
probabilities, integer counts totaling 16,384, a complete non-duplicate grid and
program/options hash bindings. The largest observed probability residual across
all 50 cases was **0.493 percentage points**.

At seed 42, ideal counts were 00:8161, 11:8223. With both error rates .40, counts
were 00:4965, 01:3281, 10:3196, 11:4942: 60.47% matching outcomes, versus 60%
analytically. With p10=.40 and p01=0, P(11)−P(00) was 19.89 percentage points,
versus 20 analytically.

These are saved computational-basis simulation observations, not device
calibration, entanglement certification, independent physical repetitions or
completed hosted Marqov jobs. Shared random seeds can correlate outcomes between
settings. The figure plots seed 42; CSV/evidence retain both seeds. The cells show
only the discrete tested settings, without interpolation. No mitigation has been
applied, and no commercial QB Emulator or internal vQPU is involved.

- [Raw results, source hashes and cleanup](../evidence/2026-09-11-readout-sweep)
- [Figure, CSV and provenance](../conference/readout-sweep)

Replay without Docker:

```sh
python3 -m unittest discover -s qualification/readout_sweep -p 'test_*.py'
```

Re-render with Matplotlib available:

```sh
python3 qualification/readout_sweep/plot.py qualification/evidence/2026-09-11-readout-sweep /tmp/qb-sweep-figures
```

Repeat native execution only with the qualified CPU image already installed:

```sh
python3 qualification/readout_sweep/qualify.py --output /tmp/qb-sweep-new
```

It runs a source overlay in one non-root, network-free, read-only container with
two CPUs, 4 GiB memory and a 240-second process bound. This experiment does not
qualify a published CPU replacement image. The next scientific extension is an
independently checked mitigation experiment using a separately estimated readout
matrix; it must not be reported as complete from these forward-model results.
