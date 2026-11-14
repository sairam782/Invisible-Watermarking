# Invisible Watermarking

Research code and corrected draft for **Distribution-Preserving QIM: Histogram Detectability and Robustness Trade-offs in Invisible Watermarking**.

## Correction status

The v2 near-undetectability claim is withdrawn. Review found a duplicate-photo
alias across folds, inconsistent detector evaluation splits, and two mathematical
claims needing correction. See [CORRECTIONS.md](CORRECTIONS.md).

The corrected v3 evaluation uses **43 crops from 14 distinct source photos**.
All detector fitting, fidelity calibration and peak references stay within the
same outer training split. This remains a small exploratory study, not a
validated security system or a claim of publication readiness.

## Corrected results

| Payload | DP-QIM learned AUC | QIM learned AUC | DP / QIM test PSNR |
|---|---|---|---|
| 64 bits | 0.65 [0.63, 0.76] | 0.95 [0.91, 1.00] | 53.36 / 53.66 dB |
| 256 bits | 0.84 [0.79, 0.92] | 1.00 [1.00, 1.00] | 46.94 / 47.12 dB |
| 1,024 bits | 0.96 [0.91, 1.00] | 1.00 [1.00, 1.00] | 40.96 / 41.07 dB |

AUC is a crop-weighted mean of within-fold AUCs. Intervals are source-bootstrap
percentile intervals conditional on the fixed split and fitted models. They do
not include retraining uncertainty. An interval [1, 1] does not establish
population-perfect detection. Higher AUC means easier detection: DP-QIM is detectable.

At 64 bits and position (3,3), interpolated-PSNR robustness differences are
+34.8 pp (blur), +33.4 pp (downscaling), +20.8 pp (half contrast), -15.8 pp
(JPEG 90), -28.6 pp (JPEG 70), and -14.1 pp (noise). Histogram jitter gives
-2.7 and -7.0 pp; this stress test is **not the published UnMarker attack**.

## Paper and evidence

- [Corrected PDF](submission/Gaduputi_DP-QIM_preprint.pdf)
- [Submission source ZIP](submission/arxiv_source.zip)
- [Build and review checklist](SUBMIT.md)
- Current raw records, predictions, fold audit and dependency versions: `results/v3/`
- Superseded records retained unchanged: `results/v2/`
- The author's existing AI-assistance disclosure remains in the paper.

## Reproduce

Use Python 3.12 and the pinned environment from the corrected run:

```bash
pip install -r requirements-v3.txt
pytest -q
python -m experiments.eval_v2 curves --uv 3 3
python -m experiments.eval_v2 curves --uv 2 2
python -m experiments.eval_v2 curves --uv 4 3
python -m experiments.detect_v3
python -m experiments.tables_v2
python -m experiments.figures_v2
```

The `eval_v2`, `tables_v2` and `figures_v2` module names are retained for
compatibility, but now use v3 data. The old `detect_v2` entry point redirects
to v3. Completed raw-result paths are protected from overwrite. For a rerun,
preserve the existing `results/v3` folder elsewhere first; do not mix old and
new records. Source images must be available through scikit-image/Matplotlib;
missing inputs now fail explicitly. Dataset and crop hashes are recorded.

## Remaining limitations

One small dataset, one split, one public selection seed, simple histogram
classifiers, and no gain-invariant QIM or learned-watermark baselines.
Exact hashes do not detect near-duplicate subjects. Stronger independent
validation and a references/novelty review are still needed before submission.
