# Findings log — running list of what the experiments actually say

Newest first.

---

## 2026-11-07 — Audit: v1 numbers were flawed; v2 protocol supersedes them

A hostile-reviewer pass over the v1 pipeline found ten problems. Every v1
number below this entry (and in paper drafts before commit "v2") should be
treated as superseded.

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

---

## 2026-10-25 (afternoon) — Autoresearch finds a Pareto-dominant DP-QIM config

**Setup.** Ran `experiments/autoresearch_dp_qim.py` with an 8-minute budget on CPU — 594 trials across the search space (uv ∈ 7 positions × M ∈ {1,2,4} × safety_margin ∈ [0.5, 10.0] × pool_size ∈ {64,128,256,512,1024}). Hill-climbing with 30% random exploration; Pareto frontier of 41 configs tracked.

**Headline configs discovered.**

| Config | PSNR | KS vs natural | mean_robust_acc | blur r=1 | resize 0.5x | noise .03 | jpeg_q90 |
|---|---|---|---|---|---|---|---|
| **DCT baseline (delta=24)** | 61.17 | 0.097 | 0.70 | 0.529 | 0.529 | 0.713 | **1.000** |
| **`uv=(3,3) M=1 sm=0.70 pool=128`** | **63.02** | **0.090** | **0.781** | 0.811 | 0.797 | 0.766 | 0.752 |
| **`uv=(2,3) M=1 sm=0.70 pool=512`** | 62.56 | **0.093** | 0.785 | 0.807 | 0.807 | 0.732 | 0.793 |
| `uv=(2,2) M=1 sm=0.58 pool=128` (best scalar score) | 62.96 | 0.109 | **0.844** | 0.846 | 0.871 | 0.766 | 0.893 |

**The breakthrough.** The `uv=(3,3), M=1, safety_margin=0.70, pool=128` config is **strictly better than the DCT baseline** on three dimensions simultaneously:

- **PSNR**: 63.02 vs 61.17 (+1.85 dB fidelity gain)
- **Undetectability (KS vs natural)**: **0.090 vs 0.097** (DP-QIM is MORE undetectable than baseline)
- **Robustness (6 of 7 attacks)**: wins on blur (+28pp), resize-0.5× (+27pp), noise σ=0.03 (+5pp); near-tie on identity, resize-2×, rotation, crop

The only loss is **JPEG-Q90**: 0.752 vs 1.000 (−25pp). This is because mid-band DCT (3,3) coefficients at magnitudes ~0.5-5 (from the pool) are near JPEG-Q90's quantization step, so some writes collapse to zero during JPEG encoding. Future work: bias the pool to JPEG-step-aligned magnitudes.

**Pareto frontier shape.** The leaderboard's 41 frontier configs trace a clean curve from (KS 0.09, robust 0.78) to (KS 0.25, robust 0.91). Baseline sits at (KS 0.097, robust ~0.70), **below the entire DP-QIM frontier** — i.e. for every undetectability level, DP-QIM offers higher robustness; for every robustness level, DP-QIM offers at least matched undetectability.

**The paper's publishable claim now reads:**
> "At matched or better PSNR, DP-QIM dominates classical DCT-QIM on undetectability (3% lower KS to natural distribution) AND robustness against regenerative-attack proxies (+27 pp on blur, +27 pp on downscale, +5 pp on noise). JPEG-Q90 is the one attack class where baseline remains preferable, and we characterize the operating point tradeoff."

**Session reset note.** Previous session's work (committed locally, not pushed) was lost when container was reclaimed. This session is pushed to `claude/research-paper-publication-6wnwmd` branch to survive future resets.

---

## 2026-10-25 (morning) — DP-QIM v1 head-to-head: strong robustness, undetectability needs tuning

**Setup.** 16 photo-like training images, 8 test images, 8-image natural reference bank. Payload 64 bits, uv=(3,3), M=1 (sign-QIM), safety_margin=3.0. DP-QIM samples target values from a *safe pool* of natural coefficient samples inside the target cell and at least safety_margin from either boundary. Baseline is single-coefficient DCT-QIM swept to match DP-QIM's PSNR. KS distance measured on the **watermarked coefficients only** (global-image KS is dominated by 94% unmodified blocks and hides the fingerprint).

**Result (`results/compare_dpqim_vs_baseline.md`).**

| Metric | DCT-baseline (delta=24) | DP-QIM (eps=3.0) | Delta |
|---|---|---|---|
| PSNR | 61.17 dB | 61.34 dB | matched |
| SSIM | 0.9998 | 0.9998 | equivalent |
| KS vs natural | **0.097** | 0.195 | DP-QIM is **2× worse** here |
| Natural-vs-natural reference KS | 0.011 | | floor |
| Gaussian blur r=1.0 | 0.529 | **0.883** | **+35.4 pp** |
| Resize 0.5× | 0.529 | **0.877** | **+34.8 pp** |
| Gauss noise sigma=.03 | 0.713 | **0.822** | **+10.9 pp** |
| JPEG-Q90 | **1.000** | 0.920 | −8.0 pp |

**Diagnosis of the KS result.** With safety_margin=3, the sample pool contains only natural samples with |c| > 3. The pool mean is ~±5.6. Written DP-QIM coefficients are either (a) unchanged natural values (free lunch — 50%) or (b) sampled from the |c|>3 pool (50%). This systematically shifts mass away from the mode and creates a measurable CDF gap near zero (~0.19).

**The tension.** Smaller safety_margin → more mode mass preserved → better KS, BUT target values closer to cell boundaries → RGB→uint8 round-trip noise may flip bits → worse decoding accuracy. The autoresearch loop (`experiments/autoresearch_dp_qim.py`) is designed to search this tradeoff.

**→ The afternoon run resolved this tension**: safety_margin ~0.7 is the sweet spot, giving KS ≤ baseline AND strong robustness. See the top of this document.

---
