# How to submit this paper

**I (the AI agent) cannot press "submit" on arxiv.org for you.** arXiv
requires a verified account with phone authentication and, for a first-time
submitter in a given primary subject area, an *endorsement* from an existing
registered author. The steps below are the exact actions you need to take.

---

## Step 0 — arXiv account + endorsement (do this NOW if you haven't)

Current date: Nov 4, 2026. Target: Nov 15 submission. The endorsement step
can take 1–7 days, so **start it today**.

1. Go to <https://arxiv.org/user/register> and create an account using
   your NJIT email (`ag2936@njit.edu` — arXiv prefers an `.edu` address).
2. Verify the account via the email link.
3. Add a phone number and verify via SMS (required before first submission).
4. **Endorsement**: as a first-time cs.CR submitter you need an endorsement.
   Two options:
   - **Easiest**: ask one of your professors who has published on arXiv
     under cs.CR, cs.CV, or cs.MM (Prof. Ravneet Kaur or Prof. Arashdeep
     Kaur — check if either has arXiv papers, or ask the department).
     Send them your endorsement code from
     <https://arxiv.org/auth/need-endorsement>.
   - **Alternative**: email [arxiv@cornell.edu](mailto:arxiv@cornell.edu)
     explaining you are an M.S. student at NJIT doing a watermarking
     project; sometimes they endorse students directly.

If this step slips past Nov 15, the paper is still ready — we'll just
need to pivot to a workshop submission system (EasyChair / OpenReview)
in parallel, which does not require endorsement.

---

## Step 1 — Verify the submission package

The zip is at `arxiv_package.zip` (I sent it to you in the previous
message; you can also rebuild with:

```bash
cd Invisible-Watermarking
python -m experiments.build_arxiv_package
# Produces arxiv_package.zip in your repo's parent-tmp location.
```

Expected contents (45 KB total):
```
arxiv_package/
├── README.txt            cover note
├── main.tex              ← the paper source
├── references.bib        bibliography
├── main.bbl              pre-built bibliography (arXiv likes this)
└── figures/
    ├── fig1_histograms.pdf
    ├── fig2_pareto.pdf
    └── fig3_unmarker.pdf
```

Open `main.pdf` (I sent it) and read it end to end once before
submitting — if anything feels off, tell me and I'll fix it.

---

## Step 2 — Submit at arxiv.org/submit

1. Go to <https://arxiv.org/submit> (log in first).
2. Click **"Start new submission"**.
3. **License**: pick "arXiv.org perpetual, non-exclusive license" (the default).
4. **Primary archive**: `cs` (Computer Science).
5. **Primary subject class**: `cs.CR` (Cryptography and Security).
6. **Cross-list**: add `cs.CV` (Computer Vision).
7. **Title**: paste exactly:
   ```
   Distribution-Preserving QIM: An Invisible Watermark that Preserves the Natural DCT Marginal Distribution
   ```
8. **Authors**: `Abhishek Sairam Gaduputi`
   (affiliation: `New Jersey Institute of Technology`)
9. **Abstract**: copy the abstract from `main.tex` (lines 39-67 or so,
   between the `\begin{abstract}` and `\end{abstract}` tags, stripping
   the `\textbf{}` markup). I can regenerate a clean plaintext abstract
   on request.
10. **Comments** (optional): e.g. "6 pages, 3 figures, 4 tables. Code
    at https://github.com/sairam782/Invisible-Watermarking"
11. **Upload**: drag `arxiv_package.zip`.
12. **Process files**: arXiv's AutoTeX will try to compile. If you see
    any warnings or errors, screenshot and send them to me — I'll fix
    and rebuild the zip.
13. **Preview the generated PDF**: check that it matches our 6-page
    version. If pages are blank or figures missing, abort and let me
    know.
14. **Submit**: after confirming the preview, click Submit. arXiv's
    moderators review within ~1 business day; the paper becomes public
    at the next weekday 20:00 US-Eastern announcement.

---

## Step 3 — After submission

- **Save the submission ID** (looks like `2611.xxxxx`). I'll update the
  repo's README to link to it.
- **Tweet / LinkedIn / email**: once the arXiv listing is live, we
  draft a one-paragraph announcement you can share.
- **Pick a workshop venue**: simultaneously submit to a workshop for
  the formal review track. Candidates:
  - **IEEE WIFS 2027** — deadline typically mid-September; check
    <https://wifs2027.ieeehost.org> closer to the date.
  - **IH&MMSec 2027** — deadline typically January.
  - **SaTML 2027** — deadline typically October.
  Workshop submissions via EasyChair / OpenReview do not require
  arXiv-style endorsement.

---

## Step 4 — If arXiv endorsement is delayed

If the endorsement does not come through by Nov 15:

1. Submit to a workshop or preprint venue that doesn't require it.
   Good first-paper venues:
   - **OpenReview.net** — accepts arbitrary tech reports, no gating.
   - **SSRN** — accepts academic preprints across disciplines.
   - **HAL (hal.science)** — open archive, accepts without endorsement.
2. The paper is complete and defensible regardless of venue; arXiv is
   just the most-visible one.

---

## What I will do in the meantime

While you're doing Step 0 (account + endorsement), I will:

1. Add 3–5 more adaptive-QIM citations to strengthen related work.
2. Final cross-read of the draft for any remaining rough edges.
3. Prepare a plaintext abstract (for step 2.9) and a one-paragraph
   LinkedIn announcement (for step 3).
4. Monitor if you report any AutoTeX errors during upload.

Ping me when you've done Step 0, or when you hit any snag.
