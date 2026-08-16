# Research Plan

## Working title
**Perceptually-Masked Hybrid DCT-DWT Invisible Watermarking Robust to Common and Regenerative Attacks**

## Motivation
Deepfake abuse relies on freely re-using and re-generating images without provenance. Invisible watermarking is a proactive defense: a payload embedded at content creation survives common image-processing pipelines and reveals whether a suspected deepfake was derived from a watermarked source. Learned watermarking (HiDDeN, StegaStamp, StableSignature) is state of the art, but (a) is expensive to train, (b) transfers poorly across image domains, and (c) fails against diffusion-purification attacks. Classical frequency-domain watermarks are cheap and interpretable but degrade under aggressive JPEG and light regeneration.

## Thesis
A **hybrid DCT + DWT** embedding, gated by a **perceptual visibility mask** derived from local frequency energy, achieves:
1. Higher payload capacity per unit PSNR than DCT-only or DWT-only baselines,
2. Comparable bit-accuracy to HiDDeN under common attacks (JPEG-Q40, crop-70%, resize, Gaussian noise, blur), and
3. Meaningfully better bit-accuracy than HiDDeN under **light regenerative attacks** (VAE re-encode, low-strength diffusion purification), because energy is distributed across two transforms rather than a single learned feature space that the regenerator quickly aligns to.

## Contribution (paper delta)
1. A closed-form perceptual mask that allocates payload bits between DCT mid-band and DWT-HL/LH sub-bands based on local activity — replaces hand-tuned per-band strengths in prior work.
2. A **benchmark harness** for invisible watermarking that includes regenerative attacks (VAE round-trip, low-step DiffPure), released with the paper.
3. Empirical study across attacks × payload sizes × host distributions (natural images, faces, AI-generated images).

## Baselines to reproduce
- DCT mid-frequency (Cox et al., 1997) — our own implementation.
- DWT-HL/LH (Xia et al., 1998) — our own implementation.
- HiDDeN (Zhu et al., ECCV 2018) — small re-implementation, trained on ~10k images.
- (Stretch) StegaStamp (Tancik et al., CVPR 2020) — use pretrained if available.

## Datasets
- DIV2K (train, small subset) — natural images.
- CelebA-HQ subset — faces (deepfake-relevant).
- Small set of Stable-Diffusion-generated images — AI-generated hosts.
- Held-out validation: Kodak (24 images), plus 100 CelebA-HQ, plus 100 SD.

## Attacks (harness)
Common: JPEG Q∈{90,70,40,20}, Gaussian noise σ∈{0.01,0.03,0.05}, Gaussian blur k∈{3,5,7}, center-crop {90%,70%,50%}, resize↕{0.5×,2×}, rotation ±{5°,15°}.
Regenerative: VAE round-trip (SD-VAE), DiffPure @ {50, 100} steps, Real-ESRGAN upscale-then-downscale.

## Metrics
Fidelity: PSNR, SSIM, LPIPS (on cover vs watermarked).
Robustness: bit-accuracy (mean over payload bits), payload-recovery rate (≥1-BER threshold).
Cost: encode/decode time per image, memory.

## Target venue
- Primary: **IEEE WIFS 2026** (Workshop on Information Forensics and Security) — small venue, fast turnaround, watermarking is core topic.
- Secondary: **IH&MMSec 2026** (ACM Info Hiding & Multimedia Security).
- Stretch: **CVPR 2027** — needs stronger novelty (adversarial-trained variant).

## Timeline (aggressive)
- Weeks 1–2: DCT + DWT baselines + attack harness + numbers on Kodak.
- Weeks 3–4: HiDDeN re-implementation + trained on DIV2K.
- Weeks 5–6: Hybrid method + perceptual mask; ablations.
- Weeks 7–8: Regenerative-attack experiments; full result tables.
- Weeks 9–10: Paper drafting; figures; submission.

## Non-goals (kept out of v1)
- Video watermarking.
- Audio watermarking (deferred to v2 despite prof suggestion — separate modality needs its own harness).
- Adversarial training against a specific attacker network (candidate for v2).
