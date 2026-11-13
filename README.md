# Invisible Watermarking

Research code and paper for **Distribution-Preserving QIM (DP-QIM)**, a
QIM-style invisible image watermark that leaves the natural DCT coefficient
distribution intact.

## Paper

*Distribution-Preserving QIM: Trading Noise Margin for Statistical
Undetectability and Scaling Robustness in Invisible Watermarking* —
Abhishek Sairam Gaduputi (NJIT).

- PDF: [`submission/Gaduputi_DP-QIM_preprint.pdf`](submission/Gaduputi_DP-QIM_preprint.pdf)
- Preprint: *(link added once posted)*
- How to submit / rebuild: [`SUBMIT.md`](SUBMIT.md)

Main findings (44 real crops, 15 photos, same DCT position, matched PSNR,
95% source-bootstrap CIs):

| | DP-QIM vs. classical QIM |
|---|---|
| Learned-detector ROC-AUC, 64 bits | 0.52 vs 0.90 (near-undetectable) |
| Blur / 0.5× downscale / 0.5× contrast | +35 / +34 / +20 pp bit accuracy |
| JPEG Q70 / Gaussian noise | −28 / −14 pp |
| UnMarker-style removal | −3 to −7 pp |

## Layout

```
src/            core library (encoders, decoders, attacks, metrics, protocol)
experiments/    scripts producing results/ and the paper's tables and figures
tests/          pytest suite
paper/          LaTeX manuscript (paper/main.tex)
results/v2/     results reported in the paper
submission/     files to upload to TechRxiv / arXiv
FINDINGS.md     research log, including the v1 audit
```

## Reproduce the paper

```bash
pip install -r requirements.txt
pytest -q
python -m experiments.eval_v2 curves --uv 3 3
python -m experiments.eval_v2 curves --uv 2 2
python -m experiments.eval_v2 curves --uv 4 3
python -m experiments.detect_v2
python -m experiments.tables_v2
python -m experiments.figures_v2
```
