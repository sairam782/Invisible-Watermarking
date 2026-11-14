# Corrected draft: build and pre-submission checklist

The v3 PDF supersedes the earlier near-undetectability claims. Read
[CORRECTIONS.md](CORRECTIONS.md) and the Limitations before using it.
No submission or external message has been sent by this correction workflow.

## Files

- `submission/Gaduputi_DP-QIM_preprint.pdf`: corrected paper.
- `submission/arxiv_source.zip`: matching LaTeX source package.
- `submission/ABSTRACT_PLAINTEXT.txt`: corrected title and abstract.
- `paper/handout.pdf`: short summary, not a substitute for the paper.

## Before any submission

1. Read and verify every claim, including both corrected propositions.
2. Inspect `results/v3/detect_audit.json`, the per-example scores and crop hashes.
3. Do not reuse the old v2 metrics or descriptions of statistical invisibility.
4. Obtain an independent scientific review. Broader datasets, stronger detectors
   and gain-invariant QIM baselines remain important gaps.
5. Verify the intended server/venue's current scope, submission requirements,
   licensing options, endorsement rules, AI-use policy and formatting yourself.
   Do not assume a posting or acceptance date.
6. Check author affiliation, conflicts, funding, dataset permissions and disclosure
   for accuracy. Preserve the paper's AI-assistance acknowledgment and answer
   submission questions truthfully.
7. Confirm the public code link and that uploaded PDF and source ZIP match.

A preprint is not peer reviewed. The old date-based submission instructions are
not a scientific-readiness assessment.

## Rebuild after changing the manuscript

```bash
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
pdflatex handout
cd ..
python -m experiments.build_arxiv_package --out /path/to/a/new/arxiv_package
cp paper/main.pdf submission/Gaduputi_DP-QIM_preprint.pdf
cp /path/to/a/new/arxiv_package.zip submission/arxiv_source.zip
cp paper/ABSTRACT_PLAINTEXT.txt submission/ABSTRACT_PLAINTEXT.txt
```

Review the rendered PDF and verify the source package before uploading.
