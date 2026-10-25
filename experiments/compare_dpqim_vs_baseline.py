"""Head-to-head: DCT baseline vs DP-QIM at matched PSNR.

Sweeps DCT baseline delta to find configs whose PSNR matches DP-QIM's, then
compares (a) bit-accuracy across the attack suite, (b) KS-distance to natural
on the WATERMARKED coefficients only (global-image KS is dominated by
unmodified blocks and hides the fingerprint), (c) fidelity.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.fftpack import dct as _dct

from src.attacks import AttackSuite
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import decode as dct_decode
from src.dct_watermark import encode as dct_encode
from src.dp_qim_watermark import DPQIMConfig, DEFAULT_UV, _block_order
from src.dp_qim_watermark import decode as dp_decode
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import bit_accuracy, psnr, ssim
from src.natural_cdf import BLOCK, collect_dct_coeffs, fit_natural_cdfs, load_cdfs
from src.utils import block_view, pad_to_multiple, random_bits, rgb_to_ycbcr

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"


def _dct2(x):
    return _dct(_dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _photo(seed, h=256, w=256):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = 128 + 40 * np.sin(xx / 30.0) + 30 * np.cos(yy / 25.0)
    tex = rng.laplace(0.0, 6.0, size=(h, w))
    y = np.clip(base + tex, 0, 255)
    rgb = np.stack([y, np.roll(y, 3, 0), np.roll(y, 3, 1)], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _extract_watermarked_coeffs(img, uv, payload_bits, seed):
    y = rgb_to_ycbcr(img)[..., 0]
    y_pad, _ = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    order = _block_order(hb, wb, y.shape, payload_bits, seed)
    return _dct2(blocks).reshape(hb * wb, BLOCK, BLOCK)[order, uv[0], uv[1]]


def _ks(a, b):
    return float(stats.ks_2samp(a, b).statistic)


def sweep_baseline(images, nat_coeffs, uv, deltas, payload_bits):
    suite = AttackSuite.default()
    out = []
    for d in deltas:
        cfg = DCTWatermarkConfig(delta=d, payload_bits=payload_bits, seed=1337)
        per_atk = {a[0]: [] for a in suite.attacks}
        psnrs, ssims, kss = [], [], []
        for name, img in images:
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


def write_report(baseline_rows, dp_row, natural_ks_self, out_md):
    match = min(baseline_rows, key=lambda r: abs(r["psnr"] - dp_row["psnr"]))
    gap = abs(match["psnr"] - dp_row["psnr"])
    lines = [
        f"# DCT baseline vs DP-QIM — matched-PSNR head-to-head",
        "",
        f"Position: uv={DEFAULT_UV}, payload=64 bits, 8 test photos.",
        "",
        "## Undetectability (KS vs natural, measured on watermarked coeffs only)",
        "",
        f"- Natural-vs-natural reference: **{natural_ks_self:.4f}**",
        f"- DCT-baseline (delta={match['delta']}): **{match['ks']:.4f}**",
        f"- DP-QIM: **{dp_row['ks']:.4f}**",
        f"- DP-QIM is **{match['ks']/max(dp_row['ks'],1e-9):.2f}x more undetectable**",
        "",
        "## Fidelity",
        "",
        "| Method | PSNR | SSIM |",
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
    out_md.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cdf-path", type=Path,
                    default=REPO_ROOT / "results" / "natural_cdfs_M1.npz")
    ap.add_argument("--payload", type=int, default=64)
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    if not args.cdf_path.exists():
        print(f"{args.cdf_path} not found — fitting fresh M=1 CDFs")
        train = [_photo(i) for i in range(16)]
        tc = collect_dct_coeffs(train)
        cdfs = fit_natural_cdfs(tc, m=1)
        from src.natural_cdf import save_cdfs
        save_cdfs(cdfs, args.cdf_path)
    else:
        cdfs = load_cdfs(args.cdf_path)

    test_imgs = [(f"test_{i:02d}", _photo(1000 + i)) for i in range(8)]
    nat_ref = [_photo(2000 + i) for i in range(8)]
    nat_bank = collect_dct_coeffs(nat_ref)[..., DEFAULT_UV[0], DEFAULT_UV[1]].flatten()
    mid = nat_bank.size // 2
    nat_ks_self = _ks(nat_bank[:mid], nat_bank[mid:])
    print(f"natural-vs-natural KS reference: {nat_ks_self:.4f}")

    print("\nsweeping DCT baseline...")
    baseline = sweep_baseline(
        test_imgs, nat_bank, DEFAULT_UV,
        deltas=[8, 12, 16, 20, 24, 32, 48, 64],
        payload_bits=args.payload,
    )
    for r in baseline:
        print(f"  delta={r['delta']:3d}  PSNR={r['psnr']:.2f}  KS={r['ks']:.4f}")

    print("\nevaluating DP-QIM...")
    dp = eval_dpqim(test_imgs, nat_bank, DEFAULT_UV, cdfs, args.payload)
    print(f"  DP-QIM  PSNR={dp['psnr']:.2f}  KS={dp['ks']:.4f}")

    out_md = RESULTS / "compare_dpqim_vs_baseline.md"
    write_report(baseline, dp, nat_ks_self, out_md)
    print(f"\nwrote {out_md}")

    csv_path = RESULTS / "compare_dpqim_vs_baseline.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "delta", "psnr", "ssim", "ks", "attack", "bit_accuracy"])
        for r in baseline + [dp]:
            for atk, acc in r["per_attack"].items():
                w.writerow([r["method"], r["delta"], r["psnr"], r["ssim"], r["ks"], atk, acc])


if __name__ == "__main__":
    main()
