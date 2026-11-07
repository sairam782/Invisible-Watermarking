# How to submit this paper — the actual step-by-step

**I (the AI agent) cannot press "submit" on any site for you.** Every
preprint server and conference management system requires a human
account + manual clicking. The guide below gives you the shortest
reliable paths.

---

## The decision tree (look at this first)

```
Do you have a verified arXiv account with endorsement for cs.CR?
├── YES  → go to Section A (arXiv)
└── NO   → is Nov 15 close enough that endorsement may not land in time?
           ├── YES → go to Section B (TechRxiv) — same-day posting, no
           │        endorsement. Submit here to hit the deadline.
           │        You can also submit to arXiv later (dual-posting
           │        is explicitly allowed by both).
           └── NO  → go to Section A (arXiv) and start the endorsement
                    today.
```

## A quick email you can send to a professor for the arXiv endorsement

See `ENDORSEMENT_EMAIL.txt` in this repo. Paste into your mail client,
replace `<PROFESSOR NAME>` and `<YOUR ENDORSEMENT CODE>` from
<https://arxiv.org/auth/need-endorsement>, send to any professor at
NJIT who has an arXiv cs.CR, cs.CV, or cs.MM paper.

---

# SECTION A — arXiv submission

Target: <https://arxiv.org/submit>.
Expected time once endorsed: ~30 minutes to submit; ~1 business day
until publicly listed.

## A.0 Account + endorsement (required once)

1. Register: <https://arxiv.org/user/register> (use your NJIT email).
2. Verify email.
3. Add + verify a phone number via SMS.
4. Request endorsement: <https://arxiv.org/auth/need-endorsement>.
   Send the code to a professor who's published in cs.CR, cs.CV, or
   cs.MM. See `ENDORSEMENT_EMAIL.txt`.

## A.1 Submit

Once the endorsement arrives:

1. <https://arxiv.org/submit> → **"Start new submission"**.
2. **License**: "arXiv.org perpetual, non-exclusive license" (default).
3. **Primary archive**: `cs`.
4. **Primary subject class**: `cs.CR` (Cryptography and Security).
5. **Cross-list**: add `cs.CV` (Computer Vision).
6. **Title**:
   `Distribution-Preserving QIM: An Invisible Watermark that Preserves the Natural DCT Marginal Distribution`
7. **Authors**: `Abhishek Sairam Gaduputi`
   (affiliation `New Jersey Institute of Technology`)
8. **Abstract**: paste the entire contents of `paper/ABSTRACT_PLAINTEXT.txt`
   (the top block, before the LinkedIn section).
9. **Comments**: `6 pages, 3 figures, 4 tables. Code at https://github.com/sairam782/Invisible-Watermarking`
10. **Upload**: drag `arxiv_package.zip`.
11. **Process files**: let AutoTeX compile. If it errors, screenshot
    and send to me — I'll fix and rebuild.
12. **Preview**: should match the 6-page PDF I sent.
13. **Submit**. Moderators review within ~1 business day; the paper
    becomes public at the next weekday 20:00 US-Eastern announcement.

## A.2 After submission

- Save the submission ID (format `2611.XXXXX`).
- Paste back here so I can update the repo README with the link.
- Use `paper/ABSTRACT_PLAINTEXT.txt` (bottom section) as the LinkedIn /
  Twitter post, with the arXiv URL filled in.

---

# SECTION B — TechRxiv (fastest fallback, no endorsement)

Target: <https://www.techrxiv.org>.
Expected time: ~1 business day from upload to public listing.
Dual-posting with arXiv is explicitly permitted — you can do both.

## B.1 Submit

1. Register at <https://www.techrxiv.org/register>. Use NJIT email.
   No endorsement, no SMS.
2. Verify email.
3. Dashboard → "New preprint".
4. **Title + authors**: same as Section A.
5. **Abstract**: same plaintext from `paper/ABSTRACT_PLAINTEXT.txt`.
6. **Subject categories**: Computer and Information Science →
   Security and Privacy; cross-list Computer Vision and Pattern
   Recognition.
7. **Keywords**: `invisible watermarking; DCT; QIM; deepfake
   provenance; UnMarker; distribution-preserving embedding`.
8. **Upload file**: upload the compiled `main.pdf` (NOT the zip —
   TechRxiv only takes PDF for the primary file).
9. **Supplemental files** (optional): attach `arxiv_package.zip` as
   source, plus `README.txt` from inside it.
10. **Submit for posting**. Automated plagiarism + format check
    completes in minutes; human screening ~1 business day.
11. Once posted, you get a DOI (e.g.`10.36227/techrxiv.XXXXX`).

This DOI is a real, citeable publication identifier. The "publish by
Nov 30" goal is satisfied once the TechRxiv listing is live.

---

# SECTION C — Workshop / journal (slower, in parallel)

Once the preprint is up (from A or B), submit to a formal venue for
peer review:

- **IEEE WIFS 2027** — <https://wifs2027.ieee-sp.org> (check deadline
  closer to date; typical Sept). Our paper targets this venue.
- **IH&MMSec 2027** — ACM Information Hiding & Multimedia Security,
  typical Jan deadline.
- **SaTML 2027** — Society for the Advancement of Trustworthy
  Machine Learning, typical Oct deadline.

Submission via EasyChair or OpenReview; no endorsement required.

---

# What's in your submission package

- `arxiv_package.zip` (58 KB): LaTeX source + bbl + 3 figure PDFs,
  ready to upload to arXiv (Section A step 10).
- `paper/main.pdf` (6 pages, 307 KB): compiled PDF, upload directly
  to TechRxiv (Section B step 8).
- `paper/ABSTRACT_PLAINTEXT.txt`: paste-ready abstract + LinkedIn
  draft.
- `ENDORSEMENT_EMAIL.txt`: send to a professor for the arXiv
  endorsement.
- `SUBMIT.md` (this file): the decision tree.

All of the above are in the GitHub repo on branch
`claude/research-paper-publication-6wnwmd`.
