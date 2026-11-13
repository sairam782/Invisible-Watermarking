# How to submit the paper (deadline: Nov 15)

Everything you upload is in the [`submission/`](submission/) folder of this
branch. Download it from GitHub (green **Code** button → **Download ZIP**, or
open each file and click **Download raw file**).

| File | Used for |
|---|---|
| `submission/Gaduputi_DP-QIM_preprint.pdf` | The paper (5 pages). Upload this to TechRxiv. |
| `submission/arxiv_source.zip` | LaTeX source. Upload this to arXiv (it compiles on its own). |
| `submission/ABSTRACT_PLAINTEXT.txt` | Title, abstract, comments line, categories, keywords to paste. |

An AI agent cannot create accounts or press "submit"; the steps below are yours.
Website menus change over time, so if a button has a slightly different name,
look for the closest equivalent.

---

## Step 0 — Before submitting (15 minutes, do this first)

1. **Read the PDF once, start to finish.** You are the sole author; you must be
   able to explain every claim, Propositions 1–2 and the evaluation protocol.
2. **Make the code link work.** The paper links to
   `https://github.com/sairam782/Invisible-Watermarking`.
   - Repo → **Settings** → **General** → scroll to **Danger Zone** →
     **Change visibility** → **Public** (skip if it already is).
   - Merge this branch into `main` so visitors see the v2 code:
     repo page → **Pull requests** → **New pull request** →
     base `main` ← compare `claude/research-paper-publication-6wnwmd` →
     **Create pull request** → **Merge pull request**.
3. The AI-assistance disclosure is already in the paper's Acknowledgment
   section. If a submission form asks about AI use, answer **yes** and say the
   same thing: Claude (Anthropic) was used for code development, experiment
   automation and manuscript drafting; you reviewed everything and take full
   responsibility.

---

## Step 1 — TechRxiv (recommended for Nov 15: no endorsement needed)

TechRxiv is IEEE's preprint server. Posted preprints get a citeable DOI
(`10.36227/techrxiv.…`).

1. Go to **https://www.techrxiv.org** → **Submit** (or **Log in / Sign up**).
   Create an account with your NJIT email and verify it. You may be asked to
   connect an ORCID iD — if you don't have one, create it free at
   https://orcid.org (2 minutes); it is useful for every future paper.
2. Start a new preprint submission and upload
   `Gaduputi_DP-QIM_preprint.pdf` as the main file.
3. Fill the metadata from `ABSTRACT_PLAINTEXT.txt`:
   - **Title**: *Distribution-Preserving QIM: Trading Noise Margin for
     Statistical Undetectability and Scaling Robustness in Invisible
     Watermarking*
   - **Author**: Abhishek Sairam Gaduputi — New Jersey Institute of
     Technology — ag2936@njit.edu (corresponding author)
   - **Abstract**: the abstract paragraph (plain text, no LaTeX).
   - **Keywords**: invisible watermarking; quantization index modulation;
     DCT; steganalysis; valumetric scaling; content provenance
   - **Subject / category**: Signal Processing (image processing) and/or
     Security — pick the closest options offered.
4. **License**: CC BY 4.0 is the usual choice and keeps you free to submit
   to a conference later.
5. Declarations: not previously published = yes; conflicts of interest =
   none; funding = none; AI use = yes (see Step 0.3).
6. Optionally attach `arxiv_source.zip` as supplementary material.
7. **Submit.** TechRxiv screens submissions before posting; this usually
   takes a few business days, which is why submitting **today** matters.
8. When it is posted you get a DOI and a URL. **Paste them into the chat**
   so the repo README and the LinkedIn post can be updated.

> Submitting by Nov 15 meets the "submit the draft" goal. The paper is
> "published" as a preprint once TechRxiv posts it (target: before Nov 30).

---

## Step 2 — arXiv (optional, can follow TechRxiv)

Posting on both TechRxiv and arXiv is allowed. arXiv needs an endorsement
for first-time submitters in cs.CR; this is a one-click action by any
existing cs.CR / cs.CV / eess.IV author.

1. Register at https://arxiv.org/user/register with your NJIT email.
2. Start a submission at https://arxiv.org/submit. If you need an
   endorsement, arXiv shows an **endorsement code**. Send it with
   `ENDORSEMENT_EMAIL.txt` to someone who has published in cs.CR or cs.CV
   (anyone with arXiv papers in that area; it does not make them a
   co-author or collaborator).
3. Once endorsed:
   - License: arXiv non-exclusive license (default) or CC BY 4.0.
   - Primary category **cs.CR**; cross-list **cs.CV** and **eess.IV**.
   - Upload `arxiv_source.zip` → **Process**. It should compile to the same
     5-page PDF. If arXiv reports an error, paste it into the chat.
   - Title, author, abstract and comments line from
     `ABSTRACT_PLAINTEXT.txt`.
   - **Submit**. It appears at the next announcement (Sun–Thu, 20:00 US
     Eastern) after moderation.

---

## Step 3 — Peer-reviewed venue (after the preprint)

A preprint is not peer-reviewed. To turn it into a conference paper,
submit to one of (check each site for the current deadline):

- **IEEE WIFS** (Workshop on Information Forensics and Security)
- **ACM IH&MMSec** (Information Hiding & Multimedia Security)
- **IEEE ICIP / ICASSP** (image/signal processing, 4–5 page format)

Reviewers will likely ask for (a) a standard benchmark such as Kodak or
DIV2K, (b) a gain-invariant QIM baseline such as Rational Dither
Modulation, and (c) a stronger steganalysis detector. These are the next
experiments to run before a venue submission.

---

## Rebuilding the files (if anything changes)

```bash
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main && cd ..
python -m experiments.build_arxiv_package --out /tmp/arxiv_package
cp paper/main.pdf submission/Gaduputi_DP-QIM_preprint.pdf
cp /tmp/arxiv_package.zip submission/arxiv_source.zip
cp paper/ABSTRACT_PLAINTEXT.txt submission/
```
