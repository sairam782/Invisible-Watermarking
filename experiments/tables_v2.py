"""Emit the paper's LaTeX tables directly from results/v2 (no hand-copied numbers)."""
from __future__ import annotations

import json
from pathlib import Path

from experiments.eval_v2 import matched_gain

REPO = Path(__file__).resolve().parent.parent
V2 = REPO / "results" / "v2"
TABLES = REPO / "paper" / "tables"

MAIN_MARGIN = 2.0
ROWS = [("identity", "No attack"),
        ("jpeg_q90", "JPEG $Q{=}90$"),
        ("jpeg_q70", "JPEG $Q{=}70$"),
        ("gauss_noise_.03", "Gaussian noise $\\sigma{=}0.03$"),
        ("gauss_blur_1.0", "Gaussian blur $r{=}1$"),
        ("resize_0.5", "Downscale $0.5\\times$"),
        ("contrast_0.5", "Contrast $\\times 0.5$"),
        ("contrast_0.8", "Contrast $\\times 0.8$"),
        ("unmarker_t2.0_j0.5", "UnMarker-style ($\\tau{=}2$, $j{=}0.5$)"),
        ("unmarker_t1.5_j1.0", "UnMarker-style ($\\tau{=}1.5$, $j{=}1$)")]


def _gain_cell(g):
    sig = (g["lo"] > 0) or (g["hi"] < 0)
    txt = f"{100*g['gain']:+.1f}"
    txt = f"\\textbf{{{txt}}}" if sig else txt
    return f"{txt} & [{100*g['lo']:+.1f}, {100*g['hi']:+.1f}]"


def robustness_table():
    recs = json.loads((V2 / "curves_uv33_p64.json").read_text())["records"]
    lines = [r"\begin{tabular}{lccc}", r"\toprule",
             r"Attack & DP-QIM & $\Delta$ vs.\ DCT-QIM (pp) & 95\% CI \\", r"\midrule"]
    psnr = None
    for key, label in ROWS:
        g = matched_gain(recs, MAIN_MARGIN, key, n_boot=2000)
        psnr = g["dp_psnr"]
        lines.append(f"{label} & {g['dp_value']:.3f} & {_gain_cell(g)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "robustness.tex").write_text("\n".join(lines) + "\n")
    return psnr


def ablation_table():
    keys = [("gauss_blur_1.0", "Blur"), ("resize_0.5", "Down.\\ $0.5\\times$"),
            ("contrast_0.5", "Contr.\\ $\\times0.5$"), ("jpeg_q70", "JPEG 70"),
            ("gauss_noise_.03", "Noise"), ("unmarker_t1.5_j1.0", "UnMarker")]
    lines = [r"\begin{tabular}{l" + "c" * (len(keys) + 1) + "}", r"\toprule",
             "Position & PSNR & " + " & ".join(k[1] for k in keys) + r" \\", r"\midrule"]
    for uv in ("22", "33", "43"):
        recs = json.loads((V2 / f"curves_uv{uv}_p64.json").read_text())["records"]
        cells, psnr = [], None
        for key, _ in keys:
            g = matched_gain(recs, MAIN_MARGIN, key, n_boot=1000)
            psnr = g["dp_psnr"]
            sig = (g["lo"] > 0) or (g["hi"] < 0)
            v = f"{100*g['gain']:+.0f}"
            cells.append(f"\\textbf{{{v}}}" if sig else v)
        lines.append(f"$({uv[0]},{uv[1]})$ & {psnr:.1f} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "ablation.tex").write_text("\n".join(lines) + "\n")


def detect_table():
    rows = json.loads((V2 / "detect.json").read_text())

    def cell(r, k):
        lo, hi = r[k + "_ci"]
        return f"{r[k]:.2f} [{lo:.2f}, {hi:.2f}]"

    lines = [r"\begin{tabular}{rcccc}", r"\toprule",
             r" & \multicolumn{2}{c}{Learned detector} & \multicolumn{2}{c}{Peak statistic} \\",
             r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
             r"Bits (PSNR) & DCT-QIM & DP-QIM & DCT-QIM & DP-QIM \\", r"\midrule"]
    for r in rows:
        if r["dp_margin"] != MAIN_MARGIN:
            continue
        lines.append(f"{r['payload']} ({r['dp_psnr']:.1f}) & {cell(r, 'qim_auc_learned')} & "
                     f"\\textbf{{{cell(r, 'dp_auc_learned')}}} & {cell(r, 'qim_auc_peak')} & "
                     f"\\textbf{{{cell(r, 'dp_auc_peak')}}} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "detect.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    TABLES.mkdir(parents=True, exist_ok=True)
    detect_table()
    psnr = robustness_table()
    ablation_table()
    print(f"main operating point PSNR {psnr:.2f} dB")
    for f in sorted(TABLES.glob("*.tex")):
        print(f"--- {f.name}\n{f.read_text()}")
