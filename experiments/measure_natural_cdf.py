"""Measure per-position empirical DCT CDFs on a set of natural images.

Uses scikit-image's bundled real photos plus procedurally-generated photo-like
backgrounds, so the CDF training set is representative but has zero external
download dependency.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from src.natural_cdf import collect_dct_coeffs, fit_natural_cdfs, save_cdfs

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"


def _load_skimage_photos():
    from skimage import data as skdata
    candidates = [
        ("astronaut", skdata.astronaut),
        ("chelsea", skdata.chelsea),
        ("coffee", skdata.coffee),
        ("cat", skdata.cat),
        ("rocket", skdata.rocket),
    ]
    out = []
    for name, fn in candidates:
        try:
            arr = np.asarray(fn(), dtype=np.uint8)
            if arr.ndim == 2:
                arr = np.stack([arr] * 3, axis=-1)
            elif arr.shape[-1] == 4:
                arr = arr[..., :3]
            if arr.ndim == 3 and arr.shape[-1] == 3:
                out.append((name, arr))
        except Exception:
            continue
    return out


def _synthetic_photolike(n, size=256, seed=0):
    out = []
    for i in range(n):
        rng = np.random.default_rng(seed + i)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        base = 128 + 40 * np.sin(xx / (25.0 + i)) + 30 * np.cos(yy / (20.0 + i))
        texture = rng.laplace(0.0, 6.0, size=(size, size))
        y = np.clip(base + texture, 0, 255)
        rgb = np.stack([y, np.roll(y, 3 + i, 0), np.roll(y, 3 + i, 1)], axis=-1)
        out.append((f"synth_{i:02d}", np.clip(rgb, 0, 255).astype(np.uint8)))
    return out


def _crop_block_multiple(arr, block=8):
    h, w = arr.shape[:2]
    return arr[: (h // block) * block, : (w // block) * block]


def run(m, extra_synth, safety_margin, tag):
    photos = _load_skimage_photos() + _synthetic_photolike(extra_synth)
    if not photos:
        raise SystemExit("no images available")

    print(f"loaded {len(photos)} images:")
    total_blocks = 0
    prepared = []
    for name, img in photos:
        img = _crop_block_multiple(img)
        blocks = (img.shape[0] // 8) * (img.shape[1] // 8)
        total_blocks += blocks
        prepared.append(img)
        print(f"  {name:12s}  shape={img.shape}  blocks={blocks}")
    print(f"total blocks: {total_blocks}")

    print(f"\nfitting M={m} ({2*m} cells per position), safety_margin={safety_margin}...")
    coeffs = collect_dct_coeffs(prepared)
    cdfs = fit_natural_cdfs(coeffs, m=m, safety_margin=safety_margin)
    print(f"fitted {len(cdfs)} non-DC positions")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_npz = RESULTS / f"natural_cdfs_{tag}.npz"
    save_cdfs(cdfs, out_npz)
    print(f"wrote {out_npz}")

    # summary stats
    lines = [
        f"# Natural DCT CDFs — M={m}, {total_blocks} blocks across {len(photos)} images",
        "", "Per-position statistics of raw DCT coefficients (skipping DC).", "",
        "`std_ratio` = 99th percentile / 50th percentile (larger = heavier-tailed).", "",
        "| (u,v) | mean | std | median | 99th %ile | std_ratio |",
        "|---|---|---|---|---|---|",
    ]
    key_positions = [(0,1),(1,0),(1,1),(2,2),(3,3),(4,4),(4,3),(3,4),(5,5),(7,7)]
    for (u, v) in key_positions:
        s = coeffs[:, u, v]
        p50 = float(np.percentile(np.abs(s), 50))
        p99 = float(np.percentile(np.abs(s), 99))
        ratio = p99 / max(p50, 1e-6)
        lines.append(
            f"| ({u},{v}) | {s.mean():+.3f} | {s.std():.3f} | {np.median(s):+.3f} | "
            f"{p99:.3f} | {ratio:.2f} |"
        )

    out_md = RESULTS / f"natural_cdfs_{tag}.md"
    out_md.write_text("\n".join(lines) + "\n")
    print(f"wrote {out_md}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m", type=int, default=1)
    ap.add_argument("--extra-synth", type=int, default=8)
    ap.add_argument("--safety-margin", type=float, default=3.0)
    ap.add_argument("--tag", type=str, default=None)
    args = ap.parse_args()
    tag = args.tag or f"M{args.m}"
    run(args.m, args.extra_synth, args.safety_margin, tag)


if __name__ == "__main__":
    main()
