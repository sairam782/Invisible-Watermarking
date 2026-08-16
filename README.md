# Invisible Watermarking

Research code and paper draft for a new invisible watermarking method aimed at protecting media against deepfake misuse.

## Layout

```
src/            core library (encoders, decoders, attacks, metrics)
experiments/    runnable scripts producing tables/figures in results/
tests/          pytest suite
paper/          LaTeX manuscript (paper/main.tex)
results/        generated tables (CSV), figures (PNG/PDF)
data/           local datasets (gitignored)
RESEARCH.md     thesis, contribution, related work
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m experiments.baseline_dct --image data/sample.png
```

See `RESEARCH.md` for the research plan.
