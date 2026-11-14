"""Figures for the corrected v3 paper (historical filenames retained).

fig1_histograms_v2: DCT(3,3) coefficient histograms over all blocks of the
    43 real crops - cover vs DCT-QIM stego vs DP-QIM stego, both methods at
    the same position and matched PSNR, every block carrying payload.
fig2_curves_v2:     bit accuracy vs PSNR for six attacks, both methods.
fig3_detect_v2:     detector ROC-AUC vs payload density with 95% CIs.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parent.parent
V2 = REPO / "results" / "v3"
FIGS = REPO / "paper" / "figures"

DP_COLOR, QIM_COLOR = "#C0392B", "#555555"


def _save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGS / f"{name}.png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {FIGS / name}.pdf")


def fig1():
    from experiments.detect_v3 import UV, _stego_sets
    from src.protocol import block_dct, real_crops
    crops = real_crops()
    payload = 1024
    dp, dp_psnr, (delta, q, q_psnr) = _stego_sets(crops, payload, margin=2.0)
    cover = np.concatenate([block_dct(c.image)[:, UV[0], UV[1]] for c in crops])
    q_c = np.concatenate([block_dct(q[c.name])[:, UV[0], UV[1]] for c in crops])
    d_c = np.concatenate([block_dct(dp[c.name])[:, UV[0], UV[1]] for c in crops])
    bins = np.arange(-60.5, 61.5, 1.0)
    fig, axes = plt.subplots(1, 3, figsize=(10, 2.8), sharey=True)
    for ax, data, title, col in [
        (axes[0], cover, "Cover (natural)", "#2E86C1"),
        (axes[1], q_c, f"QIM, train-calibrated ({q_psnr:.1f} dB)", QIM_COLOR),
        (axes[2], d_c, f"DP-QIM, $\\epsilon$=2 ({dp_psnr:.1f} dB)", DP_COLOR),
    ]:
        ax.hist(np.clip(data, -60, 60), bins=bins, density=True, color=col)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel(f"DCT{UV} coefficient", fontsize=8)
        ax.set_yscale("log")
        ax.tick_params(labelsize=7)
    axes[0].set_ylabel("density (log)", fontsize=8)
    plt.tight_layout()
    _save(fig, "fig1_histograms_v2")


def fig2(path=V2 / "curves_uv33_p64.json"):
    recs = json.loads(path.read_text())["records"]
    panels = [("gauss_blur_1.0", "Gaussian blur r=1"),
              ("resize_0.5", "Downscale 0.5x"),
              ("contrast_0.5", "Contrast x0.5"),
              ("jpeg_q70", "JPEG Q70"),
              ("gauss_noise_.03", "Gaussian noise $\\sigma$=.03"),
              ("unmarker_t1.5_j1.0", "Histogram-jitter removal")]
    fig, axes = plt.subplots(2, 3, figsize=(10, 5.2), sharey=True)
    for ax, (metric, title) in zip(axes.flat, panels):
        for method, col, mk in (("DCT-QIM", QIM_COLOR, "s"), ("DP-QIM", DP_COLOR, "o")):
            params = sorted({r["param"] for r in recs if r["method"] == method})
            xs, ys = [], []
            for p in params:
                rs = [r for r in recs if r["method"] == method and r["param"] == p]
                xs.append(np.mean([r["psnr"] for r in rs]))
                ys.append(np.mean([r[metric] for r in rs]))
            if method == "DCT-QIM":
                o = np.argsort(xs)
                ax.plot(np.array(xs)[o], np.array(ys)[o], marker=mk, ms=3.5, color=col,
                        label="DCT-QIM ($\\Delta$ sweep)")
            else:   # PSNR is not monotone in the margin, so show points, not a line
                ax.scatter(xs, ys, marker=mk, s=18, color=col, zorder=3,
                           label="DP-QIM ($\\epsilon$ sweep)")
        ax.set_title(title, fontsize=9)
        ax.axhline(0.5, color="black", lw=0.5, ls="--", alpha=0.4)
        ax.set_ylim(0.4, 1.02)
        ax.grid(alpha=0.25)
        ax.tick_params(labelsize=7)
    for ax in axes[1]:
        ax.set_xlabel("PSNR of watermarked image (dB)", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("bit accuracy after attack", fontsize=8)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=8, frameon=False)
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    _save(fig, "fig2_curves_v2")


def fig3(path=V2 / "detect.json"):
    rows = [r for r in json.loads(path.read_text()) if r["dp_margin"] == 2.0]
    payloads = [r["payload"] for r in rows]
    x = np.arange(len(payloads))
    fig, axes = plt.subplots(1, 2, figsize=(8, 2.9), sharey=True)
    for ax, det, title in ((axes[0], "learned", "Learned histogram detector"),
                           (axes[1], "peak", "Histogram peak statistic")):
        for k, (tag, col, lab) in enumerate((("qim", QIM_COLOR, "DCT-QIM"),
                                              ("dp", DP_COLOR, "DP-QIM"))):
            vals = np.array([r[f"{tag}_auc_{det}"] for r in rows])
            ci = np.array([r[f"{tag}_auc_{det}_ci"] for r in rows])
            err = np.vstack([vals - ci[:, 0], ci[:, 1] - vals])
            ax.bar(x + (k - 0.5) * 0.36, vals, 0.36, yerr=err, capsize=3,
                   color=col, label=lab)
        ax.axhline(0.5, color="black", lw=0.7, ls="--")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{p} bits" for p in payloads], fontsize=8)
        ax.set_title(title, fontsize=9)
        ax.set_ylim(0.3, 1.05)
        ax.tick_params(labelsize=7)
    axes[0].set_ylabel("Within-fold ROC-AUC (0.5 = chance)", fontsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, fontsize=8, frameon=False)
    plt.tight_layout(rect=(0, 0, 1, 0.92))
    _save(fig, "fig3_detect_v2")


if __name__ == "__main__":
    fig3()
    fig2()
    fig1()
