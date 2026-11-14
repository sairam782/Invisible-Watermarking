# Scientific correction record (v3), 2026-11-13

This record supersedes the scientific claims in commit
bf2f3b05383bc67cd91f4b0207b4d68f8b63d5f7. Original numerical files in
`results/v2/` are retained unchanged and explicitly marked superseded.
The old manuscript and figures remain recoverable from that commit.

## Corrections

1. **Duplicate-source leakage.** `skimage.data.cat()` and `chelsea()` are
   pixel-identical. Their identical crops previously occupied different folds.
   The alias is removed, full images are content-deduplicated, duplicate crop
   hashes are rejected, and each outer split verifies both identity and content
   separation. The corrected set is 43 crops from 14 distinct photos.
   Loading missing required photos now fails instead of silently shrinking data.

2. **Detector evaluation.** CDF fitting, QIM PSNR calibration, feature scaling,
   logistic regression and peak references now use the same outer training
   sources. QIM's step is calibrated by training-mean PSNR only. Held-out
   PSNR differences are retained and reported, not tuned away. All predicted
   scores, fold identities, boundaries and chosen steps are saved. The original
   leave-one-source-out peak reference is replaced with an outer-training-only
   reference. AUC is a test-crop-weighted average of within-fold AUCs, avoiding
   cross-ranking decision scores from different fitted models. 2,000-resample
   source CIs are conditional on the fitted models and fixed split; they do
   not claim to measure retraining or population uncertainty.

3. **Proposition 1.** Under continuous equal-mass cells and ideal independent
   sampling, the correct mixture is `0.5 F + 0.25 G0 + 0.25 G1`, where each
   Gi conditions within its own safe cell. This is not generally global
   conditioning outside the margin. An asymmetric 3:1 safe-mass example is
   included in regression tests. The proof's limit is idealized, not an
   exact guarantee for capped pools, empirical ties or RGB rounding. Pool
   membership at zero margin now agrees with the decoder's boundary convention.

4. **Proposition 2.** The small-displacement bound is sufficient, not necessary.
   Correct QIM decoding depends on displacement modulo the lattice period.
   With delta=16, c=32 and scale=0.5, the bit is preserved despite displacement
   exceeding delta/4. The revised theorem includes the periodic decision regions,
   excludes ties from its strict iff statement, and states the implemented
   tie rule separately. DP-QIM's positive-scaling property requires an exactly
   zero boundary; all fitted (3,3) boundaries are recorded as zero in this run.
   Blur and resizing are not guaranteed scalar DCT maps. The earlier one-axis
   Gaussian argument has been replaced with its two-dimensional qualification.

5. **Claim scope.** The jitter attack is a simplified stress test, not the
   published UnMarker implementation. References to near-undetectability,
   guaranteed prevention of selective attacks, and exact empirical distribution
   preservation are withdrawn. The title, abstract, handout and submission
   materials now describe histogram detectability and robustness trade-offs.

## Corrected evidence

| Payload | DP learned AUC | QIM learned AUC | DP / QIM held-out PSNR |
|---|---|---|---|
| 64 | 0.647 [0.629, 0.763] | 0.947 [0.909, 1.000] | 53.36 / 53.66 dB |
| 256 | 0.836 [0.791, 0.922] | 1.000 [1.000, 1.000] | 46.94 / 47.12 dB |
| 1024 | 0.955 [0.910, 1.000] | 1.000 [1.000, 1.000] | 40.96 / 41.07 dB |

These are not directly comparable to old pooled-score AUCs as a one-factor
ablation: deduplication, fitting and score aggregation all changed.
The robustness comparison at 64 bits and (3,3) gives +34.8 pp blur,
+33.4 pp downscale, +20.8 pp half contrast, -15.8 pp JPEG 90,
-28.6 pp JPEG 70, -14.1 pp noise, and -2.7/-7.0 pp histogram jitter.

## Verification and audit files

- Regression tests cover exact aliases, split coverage, content leakage,
  held-out perturbation invariance of fitted parameters, both mathematical
  counterexamples, zero-margin pool membership, and within-fold AUC invariance.
- All three robustness sweeps were rerun: 903 per-image records each.
- All six detector payload/margin settings were rerun. `detect_scores.jsonl`
  stores 2,064 class/method/detector scores and `detect_audit.json` records the
  30 outer-fold fits, crop hashes, source assignments and dependency versions.
- Tables and figures are regenerated from corrected records.
- All 46 tests pass. The five-page manuscript and one-page handout were
  rendered and visually checked; neither contains long-dash characters.
  The source ZIP matches the released sources and independently rebuilds to
  the same manuscript text.
- `requirements-v3.txt` pins the environment. Historical module/figure suffixes
  remain for compatibility; current outputs and analysis use `results/v3/`.

## Remaining limits

This corrects identified errors; it is not an independent peer review or
confirmation of novelty. The same small photo collection was used during
development, and exact hashes do not find near duplicates. One fixed split,
selection seed and per-shape noise realization limit generalization. Stronger
detectors, gain-invariant QIM, learned watermarks, independent benchmarks,
repeated fitting, and a detailed source/novelty audit remain necessary before
strong publication or security claims. No submission has been made.
