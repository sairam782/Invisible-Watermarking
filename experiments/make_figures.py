"""Generate Figures 1 and 2 for the paper.

Fig 1: histograms of DCT(3,3) coefficients across 3 image sets:
       natural (unwatermarked) vs. classical DCT-QIM vs. DP-QIM.
       Shows the lattice spikes of QIM and the natural shape of DP-QIM.

Fig 2: Pareto scatter of autoresearch trials in (KS, mean_robust_acc) plane,
       with the DCT baseline operating points overlaid as crosses.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.fftpack import dct as _dct

from src.datasets import crop_to_block_multiple, load_dataset
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import encode as dct_encode
from src.dp_qim_watermark import DPQIMConfig, DEFAULT_UV, _block_order
from src.dp_qim_watermark import encode as dp_encode
from src.natural_cdf import BLOCK, collect_dct_coeffs, fit_natural_cdfs
from src.utils import block_view, pad_to_multiple, random_bits, rgb_to_ycbcr

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"
FIGS = REPO_ROOT / "paper" / "figures"


def _dct2(x):
    return _dct(_dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _coeffs_at_uv(imgs, uv):
    """Flat list of DCT(u,v) coefficients across all 8x8 blocks of all images."""
    out = []
    for img in imgs:
        img = crop_to_block_multiple(img)
        y = rgb_to_ycbcr(img)[..., 0]
        y_pad, _ = pad_to_multiple(y, BLOCK)
        b = block_view(y_pad, BLOCK).astype(np.float32)
        d = _dct2(b)
        out.append(d[..., uv[0], uv[1]].flatten())
    return np.concatenate(out)


def _watermarked_coeffs_at_uv(wm_imgs, uv, payload_bits, seed):
    """Only the written coefficients (payload_bits per image)."""
    out = []
    for img in wm_imgs:
        img = crop_to_block_multiple(img)
        y = rgb_to_ycbcr(img)[..., 0]
        y_pad, _ = pad_to_multiple(y, BLOCK)
        blocks = block_view(y_pad, BLOCK).astype(np.float32)
        hb, wb, _, _ = blocks.shape
        order = _block_order(hb, wb, y.shape, payload_bits, seed)
        out.append(_dct2(blocks).reshape(hb * wb, BLOCK, BLOCK)[order, uv[0], uv[1]])
    return np.concatenate(out)


def fig1_histograms(real_imgs, cdfs, uv, payload_bits=64,
                    baseline_delta=32, out_path=FIGS / "fig1_histograms.pdf"):
    """Overlay histograms: natural / DCT-QIM / DP-QIM at DCT(uv) position.

    All three on one axis; QIM baseline shows prominent spikes at the
    lattice points; DP-QIM is close to natural.
    """
    bits = [random_bits(payload_bits, seed=hash(n) & 0xFFFF)
            for n, _ in [(name, i) for name, i in zip([f"i{i}" for i in range(len(real_imgs))], real_imgs)]]

    # Natural: all DCT(uv) coefficients of unwatermarked images.
    nat = _coeffs_at_uv(real_imgs, uv)

    # Classical QIM watermarked coefficients only.
    qim_cfg = DCTWatermarkConfig(delta=baseline_delta, payload_bits=payload_bits, seed=1337)
    qim_wm = [dct_encode(crop_to_block_multiple(img),
                          random_bits(payload_bits, seed=hash(f"img{i}") & 0xFFFF),
                          qim_cfg)
              for i, img in enumerate(real_imgs)]
    qim_coef = _watermarked_coeffs_at_uv(qim_wm, uv, payload_bits, qim_cfg.seed)

    # DP-QIM watermarked coefficients only.
    dp_cfg = DPQIMConfig(seed=1337, payload_bits=payload_bits, uv=uv, cdfs=cdfs)
    dp_wm = [dp_encode(crop_to_block_multiple(img),
                        random_bits(payload_bits, seed=hash(f"img{i}") & 0xFFFF),
                        dp_cfg)
             for i, img in enumerate(real_imgs)]
    dp_coef = _watermarked_coeffs_at_uv(dp_wm, uv, payload_bits, dp_cfg.seed)

    # Also natural reference for watermarked positions
    nat_at_wm_positions = _watermarked_coeffs_at_uv(real_imgs, uv, payload_bits, dp_cfg.seed)

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharex=True, sharey=True)
    xmin, xmax = np.percentile(nat, 1), np.percentile(nat, 99)
    xr = max(abs(xmin), abs(xmax))
    bins = np.linspace(-xr, xr, 60)

    for ax, data, title in zip(
        axes,
        [nat_at_wm_positions, qim_coef, dp_coef],
        [f"Natural ({uv})", f"DCT-QIM Δ={baseline_delta}", "DP-QIM (ours)"],
    ):
        ax.hist(data, bins=bins, density=True, color="steelblue",
                 edgecolor="black", linewidth=0.3)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel(f"DCT{uv} coefficient")
        ax.axvline(0, color="gray", lw=0.5)
    axes[0].set_ylabel("density")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path} and .png")


def fig2_pareto(leaderboard_json, baseline_rows, out_path=FIGS / "fig2_pareto.pdf"):
    """Scatter plot of autoresearch trials with Pareto frontier highlighted."""
    data = json.loads(Path(leaderboard_json).read_text())
    accepted = [h for h in data["history"] if h.get("accepted")]
    if not accepted:
        print(f"no accepted trials in {leaderboard_json}")
        return

    all_ks = [h["ks"] for h in accepted]
    all_rob = [h["mean_robust_acc"] for h in accepted]

    frontier = data.get("frontier", [])
    front_sorted = sorted(frontier, key=lambda f: f["ks"])
    f_ks = [f["ks"] for f in front_sorted]
    f_rob = [f["mean_robust_acc"] for f in front_sorted]

    fig, ax = plt.subplots(figsize=(5.5, 4))
    ax.scatter(all_ks, all_rob, s=8, color="lightgray",
                label=f"All trials (n={len(accepted)})", zorder=1)
    ax.plot(f_ks, f_rob, "o-", color="crimson", markersize=5,
             label=f"Pareto frontier (n={len(frontier)})", zorder=3)

    # Baseline points as crosses.
    if baseline_rows:
        bl_ks = [r["ks"] for r in baseline_rows]
        bl_rob = [np.mean([r["per_attack"][a] for a in
                          ("jpeg_q90", "gauss_blur_1.0", "gauss_noise_.03", "resize_0.5")])
                   for r in baseline_rows]
        ax.plot(bl_ks, bl_rob, "x", color="black", markersize=9, mew=2,
                 label="DCT-QIM baseline", zorder=4)

    ax.set_xlabel("KS distance to natural (lower = more undetectable)")
    ax.set_ylabel("Mean bit-accuracy on robust-attack subset")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path} and .png")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="real")
    ap.add_argument("--uv", nargs=2, type=int, default=(3, 3))
    ap.add_argument("--m", type=int, default=1)
    ap.add_argument("--safety-margin", type=float, default=2.0)
    ap.add_argument("--pool-size", type=int, default=128)
    ap.add_argument("--baseline-delta", type=int, default=32)
    ap.add_argument("--leaderboard",
                    default=RESULTS / "dpqim_autoresearch_leaderboard.json")
    args = ap.parse_args()
    uv = tuple(args.uv)

    imgs = load_dataset(args.dataset)
    imgs = [img for _, img in imgs]
    if not imgs:
        raise SystemExit(f"no images in dataset {args.dataset!r}")

    # Fit CDFs on the same set (for simplicity — Fig 1 is illustrative, not benchmarked).
    coeffs = collect_dct_coeffs([crop_to_block_multiple(img) for img in imgs])
    cdfs = fit_natural_cdfs(coeffs, m=args.m, safety_margin=args.safety_margin,
                             max_pool_size=args.pool_size)

    fig1_histograms(imgs, cdfs, uv, baseline_delta=args.baseline_delta)

    # Fig 2 depends on an autoresearch leaderboard existing.
    lb = Path(args.leaderboard)
    if lb.exists():
        # Also need baseline rows — reconstruct quickly.
        from experiments.compare_real_dataset import sweep_baseline
        nat = coeffs[..., uv[0], uv[1]].flatten()
        payload_bits = 64
        baseline_rows = sweep_baseline(
            [(f"img{i}", img) for i, img in enumerate(imgs)],
            nat, uv, deltas=[8, 16, 24, 32, 48, 64], payload_bits=payload_bits,
        )
        fig2_pareto(lb, baseline_rows)
    else:
        print(f"skip Fig 2 — no leaderboard at {lb}")


if __name__ == "__main__":
    main()
