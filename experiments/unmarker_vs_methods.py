"""Headline experiment: run the UnMarker-style peak-density attack
against both DCT baseline and DP-QIM; report post-attack bit accuracy.

This is the paper's central validation: does DP-QIM survive an attack
that specifically targets peak-density anomalies?
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from src.attacks import AttackSuite
from src.datasets import crop_to_block_multiple, load_dataset
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import decode as dct_decode
from src.dct_watermark import encode as dct_encode
from src.dp_qim_watermark import DPQIMConfig
from src.dp_qim_watermark import decode as dp_decode
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import bit_accuracy, psnr
from src.natural_cdf import collect_dct_coeffs, fit_natural_cdfs
from src.unmarker_attack import (
    UnMarkerConfig,
    attack as unmarker_attack,
    build_attacker_reference_from_cdfs,
)
from src.utils import random_bits

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-dataset", default="synth_32")
    ap.add_argument("--test-dataset", default="synth_8")
    ap.add_argument("--payload", type=int, default=64)
    ap.add_argument("--uv", nargs=2, type=int, default=(2, 2))
    ap.add_argument("--m", type=int, default=1)
    ap.add_argument("--safety-margin", type=float, default=1.30)
    ap.add_argument("--pool-size", type=int, default=512)
    ap.add_argument("--baseline-delta", type=int, default=24)
    ap.add_argument("--thresholds", nargs="+", type=float,
                    default=[1.5, 2.0, 3.0, 4.0])
    ap.add_argument("--jitter-scales", nargs="+", type=float,
                    default=[0.3, 0.5, 1.0])
    args = ap.parse_args()
    uv = tuple(args.uv)

    train = [crop_to_block_multiple(img)
             for _, img in load_dataset(args.train_dataset)]
    coeffs = collect_dct_coeffs(train)
    cdfs = fit_natural_cdfs(coeffs, m=args.m, safety_margin=args.safety_margin,
                             max_pool_size=args.pool_size)
    attacker_ref = build_attacker_reference_from_cdfs(cdfs)
    print(f"attacker reference fitted on {len(train)} images, {coeffs.shape[0]} blocks")

    test = [(n, crop_to_block_multiple(img))
             for n, img in load_dataset(args.test_dataset)]
    print(f"test set: {len(test)} images")

    rows = []
    for thr in args.thresholds:
        for js in args.jitter_scales:
            atk_cfg = UnMarkerConfig(attacker_reference=attacker_ref,
                                      peak_ratio_threshold=thr,
                                      jitter_scale=js, seed=7)
            # DCT baseline run
            dct_accs = []
            dp_accs = []
            psnrs_after = []
            for name, img in test:
                bits = random_bits(args.payload, seed=hash(name) & 0xFFFF)
                b_cfg = DCTWatermarkConfig(delta=args.baseline_delta,
                                            payload_bits=args.payload, seed=1337)
                wm_b = dct_encode(img, bits, b_cfg)
                wm_b_atk = unmarker_attack(wm_b, atk_cfg)
                dct_accs.append(bit_accuracy(bits, dct_decode(wm_b_atk, b_cfg)))

                d_cfg = DPQIMConfig(seed=1337, payload_bits=args.payload,
                                     uv=uv, cdfs=cdfs)
                wm_d = dp_encode(img, bits, d_cfg)
                wm_d_atk = unmarker_attack(wm_d, atk_cfg)
                dp_accs.append(bit_accuracy(bits, dp_decode(wm_d_atk, d_cfg)))

                # perceptual quality of attack output (averaged over methods)
                psnrs_after.append(0.5 * (psnr(img, wm_b_atk) + psnr(img, wm_d_atk)))

            row = {
                "threshold": thr, "jitter_scale": js,
                "dct_bit_acc_post_attack": float(np.mean(dct_accs)),
                "dp_bit_acc_post_attack": float(np.mean(dp_accs)),
                "mean_attack_psnr": float(np.mean(psnrs_after)),
            }
            rows.append(row)
            print(f"thr={thr:.1f}  jit={js:.1f}  "
                  f"DCT={row['dct_bit_acc_post_attack']:.3f}  "
                  f"DP={row['dp_bit_acc_post_attack']:.3f}  "
                  f"atk_psnr={row['mean_attack_psnr']:.2f}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    md = RESULTS / "unmarker_vs_methods.md"
    lines = [
        "# UnMarker-style attack: DCT baseline vs DP-QIM",
        "",
        f"Attacker reference: `{args.train_dataset}` ({len(train)} images). ",
        f"Test: `{args.test_dataset}` ({len(test)} images). "
        f"Payload: {args.payload} bits.",
        "",
        "| Threshold | Jitter scale | DCT-baseline post-attack | DP-QIM post-attack | Attack PSNR |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        dp_better = r["dp_bit_acc_post_attack"] > r["dct_bit_acc_post_attack"] + 0.02
        marker = " **★**" if dp_better else ""
        lines.append(
            f"| {r['threshold']:.1f} | {r['jitter_scale']:.1f} | "
            f"{r['dct_bit_acc_post_attack']:.3f} | "
            f"{r['dp_bit_acc_post_attack']:.3f}{marker} | "
            f"{r['mean_attack_psnr']:.2f} |"
        )
    # Summary row
    best_dp = max(rows, key=lambda r: r["dp_bit_acc_post_attack"] - r["dct_bit_acc_post_attack"])
    lines += [
        "",
        f"**Best DP-QIM advantage**: threshold={best_dp['threshold']:.1f}, "
        f"jitter_scale={best_dp['jitter_scale']:.1f} → "
        f"DP-QIM survives at **{best_dp['dp_bit_acc_post_attack']:.3f}** "
        f"vs baseline **{best_dp['dct_bit_acc_post_attack']:.3f}** "
        f"(Δ = {(best_dp['dp_bit_acc_post_attack']-best_dp['dct_bit_acc_post_attack'])*100:+.1f} pp).",
    ]
    md.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {md}")

    csv_path = RESULTS / "unmarker_vs_methods.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
