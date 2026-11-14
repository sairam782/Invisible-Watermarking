# Corrected DP-QIM draft (v3)

Distribution-Preserving QIM: Histogram Detectability and Robustness Trade-offs in Invisible Watermarking

## Build

```bash
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
pdflatex handout
```

The numbers come from `results/v3`; old `results/v2` files are superseded.
From the repository root, regenerate tables and figures with:

```bash
python -m experiments.tables_v2
python -m experiments.figures_v2
```

Historical module and figure filenames retain the v2 suffix, but their active
inputs are v3. See the root README for the full raw-data rerun procedure and
CORRECTIONS.md for the scientific changes. The PDF is a corrected draft,
not proof of publication readiness.

## Package

```bash
python -m experiments.build_arxiv_package --out /path/to/a/new/package
```

Use an empty dedicated output directory: the packager replaces its contents.
The source ZIP includes the bibliography, generated tables and referenced figures.
No preprint has been submitted or endorsed by these build commands.
