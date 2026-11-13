# Paper: Distribution-Preserving QIM

Preprint target: **TechRxiv or arXiv (cs.CR)**, submit by 2026-11-15.
Venue target after preprint: IEEE WIFS or ACM IH&MMSec (IEEE conference format).

## Build

```bash
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
pdflatex handout          # optional 1-page summary
```

## Where the numbers come from

Nothing in the paper is hand-copied. From the repository root:

```bash
python -m experiments.eval_v2 curves --uv 3 3   # results/v2/curves_uv33_p64.{json,md}
python -m experiments.eval_v2 curves --uv 2 2   # position ablation
python -m experiments.eval_v2 curves --uv 4 3
python -m experiments.detect_v2                 # results/v2/detect.{json,md}
python -m experiments.tables_v2                 # paper/tables/*.tex
python -m experiments.figures_v2                # paper/figures/*_v2.{pdf,png}
```

`FINDINGS.md` (top entry) explains why the v1 numbers were withdrawn and what
the v2 protocol fixes.

## Submission package

```bash
python -m experiments.build_arxiv_package --out /path/to/arxiv_package
```

The plain-text abstract, comments line and categories are in
`ABSTRACT_PLAINTEXT.txt`. `SUBMIT.md` in the repository root walks through
TechRxiv and arXiv submission.

## Known gaps (also listed in the paper's Limitations)

- 44 crops / 15 photos; Kodak or DIV2K not yet run.
- No gain-invariant QIM (RDM, angle QIM) or learned-watermark baselines.
- UnMarker-style attack is a reimplementation; no regeneration attacks.
- Histogram-only detectors; no rich-model / CNN steganalysis.
