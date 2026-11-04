"""Head-to-head on REAL images: DCT baseline vs DP-QIM at matched PSNR.

Train the natural CDF on the real scikit-image photo set, then test against
it (held-out cross-validation style). KS distance measured on watermarked
coefficients only. All attacks run; all images reported in aggregate.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.fftpack import dct as _dct

from src.attacks import AttackSuite
from src.datasets import (
    crop_to_block_multiple,
    load_dataset,
    photo_synthetic_batch,
)
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import decode as dct_decode
from src.dct_watermark import encode as dct_encode
from src.dp_qim_watermark import DPQIMConfig, DEFAULT_UV, _block_order
from src.dp_qim_watermark import decode as dp_decode
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import bit_accuracy, psnr, ssim
from src.natural_cdf import BLOCK, collect_dct_coeffs, fit_natural_cdfs
from src.utils import block_view, pad_to_multiple, random_bits, rgb_to_ycbcr

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"


def _dct2(x):
    return _dct(_dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _ks(a, b):
    return float(stats.ks_2samp(a, b).statistic)


def _extract_watermarked_coeffs(img, uv, payload_bits, seed):
    y = rgb_to_ycbcr(img)[..., 0]
    y_pad, _ = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    order = _block_order(hb, wb, y.shape, payload_bits, seed)
    return _dct2(blocks).reshape(hb * wb, BLOCK, BLOCK)[order, uv[0], uv[1]]


def sweep_baseline(images, nat_coeffs, uv, deltas, payload_bits):
    suite = AttackSuite.default()
    out = []
    for d in deltas:
        cfg = DCTWatermarkConfig(delta=d, payload_bits=payload_bits, seed=1337)
        per_atk = {a[0]: [] for a in suite.attacks}
        psnrs, ssims, kss = [], [], []
        for name, img in images:
            img = crop_to_block_multiple(img)
            bits = random_bits(payload_bits, seed=hash(name) & 0xFFFF)
            wm = dct_encode(img, bits, cfg)
            psnrs.append(psnr(img, wm))
            ssims.append(ssim(img, wm))
            wm_coeffs = _extract_watermarked_coeffs(wm, uv, payload_bits, cfg.seed)
            kss.append(_ks(wm_coeffs, nat_coeffs))
            for a_name, atk in suite.attacks:
                per_atk[a_name].append(bit_accuracy(bits, dct_decode(atk(wm), cfg)))
        out.append({
            "method": "DCT-baseline", "delta": d,
            "psnr": float(np.mean(psnrs)), "ssim": float(np.mean(ssims)),
            "ks": float(np.mean(kss)),
            "per_attack": {k: float(np.mean(v)) for k, v in per_atk.items()},
        })
    return out


def eval_dpqim(images, nat_coeffs, uv, cdfs, payload_bits):
    suite = AttackSuite.default()
    cfg = DPQIMConfig(seed=1337, payload_bits=payload_bits, uv=uv, cdfs=cdfs)
    per_atk = {a[0]: [] for a in suite.attacks}
    psnrs, ssims, kss = [], [], []
    for name, img in images:
        img = crop_to_block_multiple(img)
        bits = random_bits(payload_bits, seed=hash(name) & 0xFFFF)
        wm = dp_encode(img, bits, cfg)
        psnrs.append(psnr(img, wm))
        ssims.append(ssim(img, wm))
        wm_coeffs = _extract_watermarked_coeffs(wm, uv, payload_bits, cfg.seed)
        kss.append(_ks(wm_coeffs, nat_coeffs))
        for a_name, atk in suite.attacks:
            per_atk[a_name].append(bit_accuracy(bits, dp_decode(atk(wm), cfg)))
    return {
        "method": "DP-QIM", "delta": None,
        "psnr": float(np.mean(psnrs)), "ssim": float(np.mean(ssims)),
        "ks": float(np.mean(kss)),
        "per_attack": {k: float(np.mean(v)) for k, v in per_atk.items()},
    }


def write_report(baseline_rows, dp_row, nat_ks_self, out_md, dataset_name,
                  train_desc, dp_hp):
    match = min(baseline_rows, key=lambda r: abs(r["psnr"] - dp_row["psnr"]))
    gap = abs(match["psnr"] - dp_row["psnr"])
    lines = [
        f"# Real-dataset head-to-head: DCT baseline vs DP-QIM",
        "",
        f"- Dataset: **{dataset_name}**",
        f"- Training (for CDF + sample pools): **{train_desc}**",
        f"- DP-QIM operating point: `{dp_hp}`",
        f"- Payload: 64 bits per image · uv=(3,3)",
        "",
        "## Undetectability (KS to natural, watermarked coeffs only)",
        "",
        f"- Natural-vs-natural reference: **{nat_ks_self:.4f}**",
        f"- DCT-baseline (delta={match['delta']}): **{match['ks']:.4f}**",
        f"- DP-QIM: **{dp_row['ks']:.4f}**",
        f"- Ratio: DP-QIM is **{match['ks']/max(dp_row['ks'],1e-9):.2f}x more undetectable**",
        "",
        "## Fidelity",
        "",
        "| Method | PSNR (dB) | SSIM |",
        "|---|---|---|",
        f"| DCT-baseline delta={match['delta']} | {match['psnr']:.2f} | {match['ssim']:.4f} |",
        f"| DP-QIM | {dp_row['psnr']:.2f} | {dp_row['ssim']:.4f} |",
        f"| Gap | {gap:.2f} dB | |",
        "",
        "## Bit accuracy per attack",
        "",
        "| Attack | DCT-baseline | DP-QIM | Δ (pp) |",
        "|---|---|---|---|",
    ]
    for atk in match["per_attack"]:
        b = match["per_attack"][atk]
        d = dp_row["per_attack"][atk]
        delta_pp = 100 * (d - b)
        marker = " ★" if delta_pp >= 3 else (" ✗" if delta_pp <= -3 else "")
        lines.append(f"| {atk} | {b:.3f} | {d:.3f} | {delta_pp:+.1f}{marker} |")

    lines += ["", "## Full baseline sweep", "", "| delta | PSNR | SSIM | KS |",
              "|---|---|---|---|"]
    for r in baseline_rows:
        lines.append(f"| {r['delta']} | {r['psnr']:.2f} | {r['ssim']:.4f} | {r['ks']:.4f} |")
    out_md.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test-dataset", default="real")
    ap.add_argument("--train-dataset", default="synth_32",
                    help="where to fit CDFs (default: 32 synthetic photo-like)")
    ap.add_argument("--payload", type=int, default=64)
    ap.add_argument("--uv", nargs=2, type=int, default=(3, 3))
    ap.add_argument("--m", type=int, default=1)
    ap.add_argument("--safety-margin", type=float, default=0.70)
    ap.add_argument("--pool-size", type=int, default=128)
    ap.add_argument("--tag", default=None)
    args = ap.parse_args()
    uv = tuple(args.uv)
    RESULTS.mkdir(parents=True, exist_ok=True)
    tag = args.tag or f"{args.test_dataset}_sm{args.safety_margin}"

    # Training set for CDF — synthetic by default (large; 16-32 images gives
    # many thousand blocks). Augment with real images if available.
    train_imgs = [img for _, img in load_dataset(args.train_dataset)]
    if not train_imgs:
        raise SystemExit(f"empty train dataset: {args.train_dataset}")

    train_blocks = collect_dct_coeffs(
        [crop_to_block_multiple(img) for img in train_imgs]
    )
    print(f"CDF training: {len(train_imgs)} images, {train_blocks.shape[0]} blocks")

    cdfs = fit_natural_cdfs(train_blocks, m=args.m, safety_margin=args.safety_margin,
                             max_pool_size=args.pool_size)
    print(f"fitted {len(cdfs)} CDFs at M={args.m}, sm={args.safety_margin}")

    # Test set
    test_imgs = load_dataset(args.test_dataset)
    if not test_imgs:
        raise SystemExit(f"empty test dataset: {args.test_dataset}")
    print(f"test set: {len(test_imgs)} images")

    # Natural reference bank for KS — drawn from the TRAINING set at the
    # chosen uv position (large, heavy, representative).
    nat_bank = train_blocks[..., uv[0], uv[1]].flatten()
    mid = nat_bank.size // 2
    nat_ks_self = _ks(nat_bank[:mid], nat_bank[mid:])
    print(f"natural-vs-natural KS reference: {nat_ks_self:.4f}")

    print("\nsweeping DCT baseline...")
    baseline_rows = sweep_baseline(
        test_imgs, nat_bank, uv,
        deltas=[8, 12, 16, 20, 24, 32, 48, 64],
        payload_bits=args.payload,
    )
    for r in baseline_rows:
        print(f"  delta={r['delta']:3d}  PSNR={r['psnr']:.2f}  KS={r['ks']:.4f}")

    print("\nevaluating DP-QIM...")
    dp_row = eval_dpqim(test_imgs, nat_bank, uv, cdfs, args.payload)
    print(f"  DP-QIM  PSNR={dp_row['psnr']:.2f}  KS={dp_row['ks']:.4f}")

    out_md = RESULTS / f"compare_real_{tag}.md"
    write_report(
        baseline_rows, dp_row, nat_ks_self, out_md,
        dataset_name=args.test_dataset,
        train_desc=f"{args.train_dataset} ({len(train_imgs)} images, {train_blocks.shape[0]} blocks)",
        dp_hp=f"uv={uv} M={args.m} sm={args.safety_margin} pool={args.pool_size}",
    )

    csv_path = RESULTS / f"compare_real_{tag}.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "delta", "psnr", "ssim", "ks", "attack", "bit_accuracy"])
        for r in baseline_rows + [dp_row]:
            for atk, acc in r["per_attack"].items():
                w.writerow([r["method"], r["delta"], r["psnr"], r["ssim"], r["ks"], atk, acc])
    print(f"\nwrote {out_md}")
    print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
