# Findings: corrected v3 evaluation

The 2026-11-13 corrections supersede the previous near-undetectability claim.
See [CORRECTIONS.md](CORRECTIONS.md) for the mathematical and protocol details.
The previous findings document is preserved at
[results/v2/LEGACY_FINDINGS.md](results/v2/LEGACY_FINDINGS.md) as a withdrawn record,
not as current evidence.

## What was corrected

- Removed the cat/chelsea duplicate alias; 43 crops from 14 distinct source images.
- Enforced source and exact-content separation; missing source data fail explicitly.
- Aligned CDF, calibration, scaler, classifier and peak-reference fitting with one
  outer training split. QIM's training-selected step is not tuned on test images.
- Replaced pooled cross-model scores with crop-weighted within-fold AUC.
- Corrected the idealized cellwise-mixture formula and periodic QIM decoding claim.
- Scoped the jitter stress test: it is not a reproduction of published UnMarker.

## Corrected observations

Learned DP-QIM AUC is 0.647 / 0.836 / 0.955 at 64 / 256 / 1,024 bits,
versus 0.947 / 1.000 / 1.000 for QIM. DP-QIM is detectable, especially at
higher payloads. Conditional confidence intervals and held-out PSNRs are
in the generated tables and results/v3.

At 64 bits, position (3,3), the matched-PSNR gain is +34.8 pp for blur,
+33.4 for downscaling and +20.8 for half contrast. JPEG 90/70 and noise
instead favor QIM by 15.8/28.6/14.1 pp. Histogram jitter favors QIM by
2.7 and 7.0 pp at the two reported settings.

These observations describe a small-sample trade-off. They do not establish
statistical invisibility, resistance to strong adaptive removal, or
state-of-the-art performance. The same photos were used during development;
stronger independent validation remains necessary.
