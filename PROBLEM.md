# Problem Statement (v2 — LOCKED 2026-10-25)

## The gap the field has just opened

As of mid-2025 the invisible-watermarking field is broken. Two attack classes have collapsed nearly every deployed scheme:

1. **UnMarker** (Barzegar & AlBadawy, IEEE S&P 2025, arXiv:2405.08363) — a fully **black-box** removal attack. Requires no knowledge of the watermarking scheme, no secret keys, no access to the detector, and no knowledge of whether the image is even watermarked. Mechanism: identify unusual regions of the image's frequency spectrum (statistical anomalies induced by the watermark), then distort them. Removes >50% of watermarks from Google SynthID, Meta StableSignature, and others in <2 min per image.

2. **Diffusion-based regeneration** (NeurIPS 2024 "Erasing the Invisible" Challenge). Even StegaStamp and TrustMark, robust to noise + JPEG, drop from near-100% to essentially chance under semantic-purification attacks.

No published defense exists (per our lit scan across 2020–2026) that specifically targets UnMarker's statistical-anomaly threat model.

## Our thesis (Spectrum-Matched DCT-QIM — "DP-QIM")

> **UnMarker succeeds because standard QIM watermarks introduce a detectable statistical fingerprint on the marginal distribution of DCT coefficients — a discrete lattice of embedded values that natural images do not exhibit. A watermark whose modifications preserve the natural per-coefficient marginal distribution should present no such anomaly.**

We propose **Distribution-Preserving QIM (DP-QIM)**: instead of snapping DCT coefficients to a uniform lattice `{ kΔ + b·Δ/2 }`, snap them to values drawn from a **CDF-partitioned empirical sample pool**. Each natural DCT position is partitioned into 2M equal-mass cells with alternating labels {0,1,...}. At encode time, if the current coefficient's cell already has the target label, no change. Else, pick a natural sample from the adjacent cell's safe pool as the new value.

## Measurable contributions

**C1. Distribution-Preserving QIM embedding rule.** For each DCT position (u,v) with per-block empirical CDF F_uv, partition the real line into 2M cells of equal natural mass, with labels alternating {0,1,...}. Encode: if current cell label == bit, no move; else, replace with a natural sample from the adjacent cell's safety-margin interior. Decode: read the cell label at the received coefficient.

**C2. Attack-aware robustness.** By drawing targets from natural samples with magnitude ≥ safety_margin, DP-QIM writes large coefficient magnitudes that survive low-pass attacks (blur, downscale) and additive noise much better than baseline QIM. Measured gains: **+35 pp on Gaussian blur r=1.0**, **+35 pp on resize 0.5×**, **+11 pp on Gaussian noise σ=0.03** at matched PSNR (61 dB).

**C3. Reproducible benchmark harness** covering common attacks (JPEG Q∈{20,40,70,90}, Gaussian noise/blur, resize, rotation, crop) plus KS-distance-to-natural as an undetectability proxy. Released with the code.

**C4. Autoresearch optimization loop** that automatically searches the DP-QIM hyperparameter space (uv position, cell count M, safety_margin, pool size) for Pareto-dominant (undetectability, robustness) operating points. First demonstration of agent-driven hyperparameter search for an invisible watermark.

## Current honest state (v1)

v1 of DP-QIM at `uv=(3,3), M=1, safety_margin=3.0` **wins on robustness** against regenerative-proxy attacks (blur, downscale, noise) by 10–35 percentage points but **loses undetectability** by ~2× KS vs natural compared to baseline. See `FINDINGS.md`.

**Open question for v2:** does there exist a (uv, M, safety_margin) point that dominates baseline on BOTH robustness and KS? If yes, this is the headline paper. If no, the paper reframes as a Pareto-frontier characterization and a robustness-focused defense.

## Why this is publishable regardless of v2 outcome

| Outcome | Paper framing | Target venue |
|---|---|---|
| v2 finds Pareto-dominant point | "DP-QIM: an invisible watermark that is strictly better than classical QIM" | IEEE TIFS / S&P workshop |
| v2 only finds robustness-dominant point | "A tunable undetectability/robustness tradeoff for invisible watermarking" | IH&MMSec / WIFS |
| v2 finds no improvement over v1 | "Characterizing the undetectability/robustness Pareto frontier for CDF-partitioned QIM" | WIFS workshop |

All three are legitimate workshop/journal papers. The experimental infrastructure (attack suite + KS harness + autoresearch loop) is itself a contribution released as open-source code.

## Non-goals for v1

- Video / audio watermarking (image only).
- Full defense against arbitrary regeneration attacks (we target frequency-statistics attacks).
- Payload rates > 1 bit per block (K=1 for v1; multi-bit is future work).
- Real Stable Diffusion img2img evaluation (we use VAE-roundtrip proxies; real diffusion deferred to compute-budget-permitting).

## Execution plan

1. ✅ Measure empirical natural DCT CDFs on training set (done — `results/natural_cdfs_M1.*`)
2. ✅ Implement DP-QIM v1 with sample-pool encoding (done — `src/dp_qim_watermark.py`)
3. ✅ Head-to-head vs DCT baseline at matched PSNR (done — `results/compare_dpqim_vs_baseline.md`)
4. 🔄 **Autoresearch loop to find Pareto-dominant point** (next — `experiments/autoresearch_dp_qim.py`)
5. ⏳ CNN detector as stronger undetectability metric
6. ⏳ Reimplement UnMarker-style statistical-anomaly attack and evaluate
7. ⏳ Paper LaTeX draft + figures + submission
