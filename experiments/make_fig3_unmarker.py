"""Figure 3: grouped bar chart of UnMarker-style attack survival.

Shows post-attack bit accuracy for both methods on synthetic and real
image benchmarks, at a representative moderate attack strength.
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"
FIGS = REPO_ROOT / "paper" / "figures"


def _load(path):
    rows = []
    with path.open() as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def main():
    synth_path = RESULTS / "unmarker_vs_methods_synth.csv"
    real_path = RESULTS / "unmarker_vs_methods_real.csv"
    if not synth_path.exists() or not real_path.exists():
        raise SystemExit("run unmarker_vs_methods twice first: synth then real")

    synth = _load(synth_path)
    real = _load(real_path)

    # Pick three representative attack settings along a strength axis.
    # Keys sortable as (threshold, jitter): we want weak, medium, strong.
    def _rep(rows, thr, jit):
        for r in rows:
            if (abs(float(r["threshold"]) - thr) < 1e-6
                    and abs(float(r["jitter_scale"]) - jit) < 1e-6):
                return r
        return None

    strengths = [("Weak\n(thr=3.0, jit=0.3)", 3.0, 0.3),
                  ("Moderate\n(thr=2.0, jit=0.5)", 2.0, 0.5),
                  ("Strong\n(thr=2.0, jit=1.0)", 2.0, 1.0)]

    synth_dct = [float(_rep(synth, t, j)["dct_bit_acc_post_attack"]) for _, t, j in strengths]
    synth_dp  = [float(_rep(synth, t, j)["dp_bit_acc_post_attack"])  for _, t, j in strengths]
    real_dct  = [float(_rep(real,  t, j)["dct_bit_acc_post_attack"]) for _, t, j in strengths]
    real_dp   = [float(_rep(real,  t, j)["dp_bit_acc_post_attack"])  for _, t, j in strengths]

    fig, axes = plt.subplots(1, 2, figsize=(9, 3.5), sharey=True)
    x = np.arange(len(strengths))
    w = 0.35
    for ax, dct, dp, title in [
        (axes[0], synth_dct, synth_dp, "Synthetic benchmark"),
        (axes[1], real_dct,  real_dp,  "Real-photo set (scikit-image)"),
    ]:
        ax.bar(x - w/2, dct, w, label="DCT-QIM", color="#808080", edgecolor="black", linewidth=0.5)
        ax.bar(x + w/2, dp,  w, label="DP-QIM (ours)", color="#C33", edgecolor="black", linewidth=0.5)
        ax.axhline(0.5, color="black", lw=0.5, linestyle="--", alpha=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels([s[0] for s in strengths], fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.set_ylim(0.4, 1.02)
        ax.grid(True, alpha=0.3, axis="y")
    axes[0].set_ylabel("Post-attack bit accuracy")
    axes[0].legend(loc="lower left", fontsize=9)
    plt.tight_layout()
    FIGS.mkdir(parents=True, exist_ok=True)
    out_pdf = FIGS / "fig3_unmarker.pdf"
    out_png = FIGS / "fig3_unmarker.png"
    fig.savefig(out_pdf, bbox_inches="tight")
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_pdf} and .png")


if __name__ == "__main__":
    main()
