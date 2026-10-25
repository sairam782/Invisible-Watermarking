# Findings log — running list of what the experiments actually say

Newest first.

---

## 2026-10-25 — DP-QIM v1 head-to-head: strong robustness, undetectability needs tuning

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

**Robustness story is real.** The three large wins (+35, +35, +11 pp on blur / downscale / noise) are mechanistically explained: DP-QIM writes large coefficient magnitudes (|c|>3 drawn from pool), which survive low-pass attacks (blur, downscale) and modest additive noise much better than the baseline's lattice-aligned writes. These are the exact attack classes a regenerative attacker (VAE roundtrip, diffusion purification) exercises.

**JPEG-Q90 loss (−8 pp) is explained by the same mechanism.** Baseline at delta=24 writes exactly to ±12, which survives JPEG-Q90's step-size ~10. DP-QIM pool values are distributed over [3, 15], so some writes fall near JPEG quantization bins and collapse toward zero. Fix candidate: either (a) tune safety_margin and pool construction (autoresearch target), or (b) explicitly bias the pool toward JPEG-step-aligned magnitudes.

**Publishable framing (honest).** v1 of DP-QIM dominates the baseline on robustness-under-regenerative-attack-proxies (blur, downscale, noise) and ties or wins on crop/rotation, but it DOES NOT win on the undetectability axis at this operating point. The paper's claim becomes:
> "DP-QIM provides a *tunable* undetectability/robustness tradeoff that the baseline cannot access: the pool construction parameter controls where the method sits on this curve, and we show operating points that trade a small undetectability loss for 30+pp wins against regeneration-proxy attacks."

v2 target (autoresearch-driven): find a pool-construction setting that achieves KS ≤ baseline AND wins robustness. If no such point exists, the paper reframes as "robustness-focused" rather than "undetectability-focused."

**Session reset note.** This result was reconstructed after a previous session's work was lost (container was reclaimed; code was committed locally but not pushed per earlier instruction). All subsequent work pushes to GitHub to survive container resets.

---
