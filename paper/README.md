# Paper: Distribution-Preserving QIM

Target venue: **IEEE WIFS 2027** (Workshop on Information Forensics and Security)
or **IH&MMSec 2027** (ACM Information Hiding & Multimedia Security).
Format: IEEE conference, 6–8 pages.

## Build

Requires a LaTeX distribution with `IEEEtran` (TeX Live or MiKTeX).

```bash
cd paper
latexmk -pdf main.tex
# or:
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

Output: `main.pdf`.

## Current status

This is a **working draft**, not a submission draft. Open issues are marked
inline in red (`\todo{...}`) and orange (`\reviewer{...}` for things a reviewer
would flag). Grep for them:

```bash
grep -n "TODO\|REVIEWER-RISK" main.tex
```

## What's done

- Full structure (abstract through conclusion + reproducibility statement).
- All key numbers from `results/` reflected in Table 1.
- Honest limitations section — all v1 gaps enumerated.
- Bibliography with 16 citations covering the core prior work.

## What's missing before submission

1. **Figures** — placeholder boxes exist for:
   - Figure 1: QIM-vs-DP-QIM histogram comparison.
   - Figure 2: autoresearch Pareto frontier scatter plot.
2. **Real-dataset results** — current numbers are on 8 synthetic images.
3. **Learned-baseline comparison** — HiDDeN or similar.
4. **Actual UnMarker attack** — currently we use KS as a proxy.
5. **Payload sweep + image-size sweep**.
6. **A few more adaptive-QIM citations** for the related-work section.

## How to iterate

Edit `main.tex`, rebuild with `latexmk -pdf main.tex`, commit, push.
Numbers in Table 1 come from `results/compare_dpqim_vs_baseline.md` and
`results/dpqim_autoresearch_leaderboard.md` — regenerate those if you
re-run experiments and update the table.
