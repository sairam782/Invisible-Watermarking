"""Payload-size sweep: how do baseline and DP-QIM scale with payload bits?

Reviewers expect this. We report, for payload in {32, 64, 128, 256}:
  - PSNR for each method
  - KS distance to natural
  - Mean bit-accuracy across the robust attack subset
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.fftpack import dct as _dct_fn

from src.attacks import AttackSuite
from src.datasets import crop_to_block_multiple, load_dataset
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import decode as dct_decode
from src.dct_watermark import encode as dct_encode
from src.dp_qim_watermark import DPQIMConfig, _block_order
from src.dp_qim_watermark import decode as dp_decode
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import bit_accuracy, psnr
from src.natural_cdf import BLOCK, collect_dct_coeffs, fit_natural_cdfs
from src.utils import block_view, pad_to_multiple, random_bits, rgb_to_ycbcr

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"

ROBUST_ATTACKS = ("jpeg_q90", "gauss_blur_1.0", "gauss_noise_.03", "resize_0.5")


def _dct2(x):
    return _dct_fn(_dct_fn(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _extract_wm_coeffs(img, uv, payload_bits, seed):
    y = rgb_to_ycbcr(img)[..., 0]
    y_pad, _ = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    order = _block_order(hb, wb, y.shape, payload_bits, seed)
    return _dct2(blocks).reshape(hb * wb, BLOCK, BLOCK)[order, uv[0], uv[1]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-dataset", default="synth_16")
    ap.add_argument("--test-dataset", default="synth_8")
    ap.add_argument("--payloads", nargs="+", type=int, default=[32, 64, 128, 256])
    ap.add_argument("--uv", nargs=2, type=int, default=(2, 2))
    ap.add_argument("--m", type=int, default=1)
    ap.add_argument("--safety-margin", type=float, default=1.30)
    ap.add_argument("--pool-size", type=int, default=512)
    ap.add_argument("--baseline-delta", type=int, default=24)
    args = ap.parse_args()
    uv = tuple(args.uv)

    train = [img for _, img in load_dataset(args.train_dataset)]
    train = [crop_to_block_multiple(img) for img in train]
    train_coeffs = collect_dct_coeffs(train)
    cdfs = fit_natural_cdfs(train_coeffs, m=args.m, safety_margin=args.safety_margin,
                             max_pool_size=args.pool_size)
    nat = train_coeffs[..., uv[0], uv[1]].flatten()

    test = [(n, crop_to_block_multiple(img)) for n, img in load_dataset(args.test_dataset)]
    suite = AttackSuite.default()

    rows = []
    for method in ("DCT-baseline", "DP-QIM"):
        for payload in args.payloads:
            per_atk = {a[0]: [] for a in suite.attacks}
            psnrs, kss = [], []
            for name, img in test:
                hb_valid = (img.shape[0] // BLOCK) * (img.shape[1] // BLOCK)
                if payload > hb_valid:
                    continue
                bits = random_bits(payload, seed=hash(name) & 0xFFFF)
                if method == "DCT-baseline":
                    cfg = DCTWatermarkConfig(delta=args.baseline_delta,
                                              payload_bits=payload, seed=1337)
                    wm = dct_encode(img, bits, cfg)
                    psnrs.append(psnr(img, wm))
                    kss.append(float(stats.ks_2samp(
                        _extract_wm_coeffs(wm, uv, payload, cfg.seed), nat
                    ).statistic))
                    for a_name, atk in suite.attacks:
                        per_atk[a_name].append(bit_accuracy(bits, dct_decode(atk(wm), cfg)))
                else:
                    cfg = DPQIMConfig(seed=1337, payload_bits=payload, uv=uv, cdfs=cdfs)
                    wm = dp_encode(img, bits, cfg)
                    psnrs.append(psnr(img, wm))
                    kss.append(float(stats.ks_2samp(
                        _extract_wm_coeffs(wm, uv, payload, cfg.seed), nat
                    ).statistic))
                    for a_name, atk in suite.attacks:
                        per_atk[a_name].append(bit_accuracy(bits, dp_decode(atk(wm), cfg)))

            per_atk_mean = {k: float(np.mean(v)) if v else float("nan")
                             for k, v in per_atk.items()}
            robust = float(np.mean([per_atk_mean[a] for a in ROBUST_ATTACKS]))
            rows.append({
                "method": method, "payload": payload,
                "psnr": float(np.mean(psnrs)) if psnrs else float("nan"),
                "ks": float(np.mean(kss)) if kss else float("nan"),
                "robust": robust,
                **{f"acc_{a}": per_atk_mean[a] for a in per_atk_mean},
            })
            print(f"{method:14s}  payload={payload:4d}  "
                  f"PSNR={rows[-1]['psnr']:.2f}  KS={rows[-1]['ks']:.4f}  "
                  f"robust={robust:.3f}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    out_md = RESULTS / "payload_sweep.md"
    lines = [
        "# Payload-size sweep",
        "",
        f"Train: {args.train_dataset} · Test: {args.test_dataset}",
        f"DP-QIM: uv={uv} M={args.m} sm={args.safety_margin} · "
        f"Baseline delta={args.baseline_delta}",
        "",
        "| Method | Payload | PSNR | KS | Robust acc | JPEG-Q90 | Blur r=1 | Noise .03 | Resize 0.5 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['method']} | {r['payload']} | {r['psnr']:.2f} | "
            f"{r['ks']:.4f} | {r['robust']:.3f} | "
            f"{r['acc_jpeg_q90']:.3f} | {r['acc_gauss_blur_1.0']:.3f} | "
            f"{r['acc_gauss_noise_.03']:.3f} | {r['acc_resize_0.5']:.3f} |"
        )
    out_md.write_text("\n".join(lines) + "\n")
    print(f"\nwrote {out_md}")

    out_csv = RESULTS / "payload_sweep.csv"
    with out_csv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_csv}")


if __name__ == "__main__":
    main()
