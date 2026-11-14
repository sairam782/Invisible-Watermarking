# Findings

Why the evaluation was rebuilt, and what the v2 results say.

## 2026-11-07 — Audit: v1 numbers were flawed; v2 protocol supersedes them

A hostile-reviewer pass over the first (v1) pipeline found ten problems, so
all v1 numbers were withdrawn. The v1 scripts and results have been removed
from the repository (they remain in git history); everything in the paper
comes from the v2 protocol below.

| # | v1 flaw | Effect |
|---|---|---|
| 1 | Payload bits seeded with Python `hash()`, salted per process | not reproducible |
| 2 | UnMarker attacker's "natural reference" = DP-QIM's own sample pools | circular; inflated DP-QIM's removal robustness |
| 3 | Real-data CDFs fitted on the test images | leakage |
| 4 | Real-data table "matched fidelity" with a 5.4 dB PSNR gap | unfair comparison |
| 5 | Per-image KS on n=64 samples (null mean ~0.11) | KS differences were noise |
| 6 | Real-data margin chosen by looking at test results | selection bias |
| 7 | Autoresearch accepted configs that do not decode at identity | invalid configs on the frontier |
| 8 | No confidence intervals | no significance |
| 9 | Baseline hard-coded at DCT (4,3), DP-QIM at (2,2)/(3,3) | frequency confound on blur/downscale |
| 10 | Baseline "KS" and Fig 1 "QIM" panel measured at a position the baseline never touched | baseline fingerprint never measured |

**v2 protocol** (`src/protocol.py`, `experiments/eval_v2.py`,
`experiments/detect_v2.py`): 44 real 256x256 crops from 15 photo sources;
5 folds grouped by source; embedder CDFs and attacker reference fitted on
training sources only; both methods at the same DCT position; baseline curve
interpolated to DP-QIM's PSNR (sweep extended so interpolation never clamps);
crc32 seeds; source-level bootstrap 95% CIs; undetectability measured by
detector ROC-AUC.

**What survives** (position (3,3), payload 64, matched PSNR):
- Detectability: learned-detector AUC 0.52 [0.49, 0.57] for DP-QIM vs
  0.90 [0.78, 1.00] for DCT-QIM; at 256 bits 0.61 vs 1.00. The UnMarker peak
  statistic is at chance for DP-QIM (0.47–0.51) and 0.72–0.86 for DCT-QIM.
- Blur r=1: +35 pp; downscale 0.5x: +34 pp (CIs exclude zero).

**What reverses**: the UnMarker-style removal attack degrades DP-QIM 3–7 pp
*more* than DCT-QIM at matched PSNR (v1 claimed +12–14 pp the other way —
an artefact of flaw #2). JPEG Q90/Q70 and additive noise also favour DCT-QIM.

**Mechanism**: with M=1 DP-QIM decodes the sign of the coefficient relative
to a median that is ~0 for AC coefficients, so any attack that scales
coefficients (blur, downscale, contrast) leaves the decision unchanged. QIM's
fixed lattice is classically fragile to such valumetric scaling. Conversely,
at matched PSNR QIM concentrates its distortion into a large lattice step,
which buys margin against additive noise and requantization.

**Revised claim**: DP-QIM trades additive-noise margin for statistical
undetectability and scaling robustness. Undetectability alone does not confer
removal resistance.
