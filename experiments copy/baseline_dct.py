"""Run the DCT baseline against the default attack suite on a set of images.

Writes:
  results/baseline_dct_<tag>.csv    — per-attack per-image metrics
  results/baseline_dct_<tag>.md     — human-readable summary table

Usage:
  python -m experiments.baseline_dct                        # uses synthetic images
  python -m experiments.baseline_dct --dir data/kodak       # runs over a folder
  python -m experiments.baseline_dct --delta 12 --payload 128
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from src.attacks import AttackSuite
from src.dct_watermark import DCTWatermarkConfig, decode, encode
from src.metrics import bit_accuracy, psnr, ssim
from src.utils import load_image_rgb, random_bits

REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"


def _synthetic_batch(n: int = 8, size: int = 256) -> list[tuple[str, np.ndarray]]:
    """Generate deterministic synthetic images so the experiment runs with no data."""
    out = []
    for i in range(n):
        rng = np.random.default_rng(1000 + i)
        yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
        base = 128 + 50 * np.sin(xx / (20.0 + i)) + 40 * np.cos(yy / (25.0 + i))
        tex = rng.normal(0, 10 + i, size=(size, size))
        y = np.clip(base + tex, 0, 255)
        rgb = np.stack([y, np.roll(y, i + 1, 0), np.roll(y, i + 1, 1)], axis=-1)
        out.append((f"synthetic_{i:02d}", np.clip(rgb, 0, 255).astype(np.uint8)))
    return out


def _load_batch(directory: Path) -> list[tuple[str, np.ndarray]]:
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in exts)
    if not paths:
        raise SystemExit(f"no images found in {directory}")
    return [(p.stem, load_image_rgb(p)) for p in paths]


def run(cfg: DCTWatermarkConfig, images: list[tuple[str, np.ndarray]], tag: str) -> Path:
    suite = AttackSuite.default()
    RESULTS.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS / f"baseline_dct_{tag}.csv"

    rows: list[dict] = []
    for name, img in images:
        bits = random_bits(cfg.payload_bits, seed=hash(name) & 0xFFFF)
        wm = encode(img, bits, cfg)
        fidelity_psnr = psnr(img, wm)
        fidelity_ssim = ssim(img, wm)
        for atk_name, atk in suite.attacks:
            attacked = atk(wm)
            recovered = decode(attacked, cfg)
            rows.append({
                "image": name,
                "attack": atk_name,
                "psnr_cover_vs_wm": round(fidelity_psnr, 3),
                "ssim_cover_vs_wm": round(fidelity_ssim, 4),
                "bit_accuracy": round(bit_accuracy(bits, recovered), 4),
                "payload_bits": cfg.payload_bits,
                "delta": cfg.delta,
            })

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    _write_summary(rows, RESULTS / f"baseline_dct_{tag}.md", cfg)
    return csv_path


def _write_summary(rows: list[dict], out: Path, cfg: DCTWatermarkConfig) -> None:
    from collections import defaultdict
    per_attack: dict[str, list[float]] = defaultdict(list)
    psnrs, ssims = [], []
    for r in rows:
        per_attack[r["attack"]].append(r["bit_accuracy"])
        psnrs.append(r["psnr_cover_vs_wm"])
        ssims.append(r["ssim_cover_vs_wm"])

    lines = [
        f"# DCT Baseline — payload={cfg.payload_bits} bits, delta={cfg.delta}",
        "",
        f"Fidelity (cover vs watermarked, averaged over {len(set(r['image'] for r in rows))} images):",
        f"- PSNR: **{np.mean(psnrs):.2f} dB**  (min {np.min(psnrs):.2f})",
        f"- SSIM: **{np.mean(ssims):.4f}**",
        "",
        "| Attack | Mean bit accuracy |",
        "|---|---|",
    ]
    for atk, accs in per_attack.items():
        lines.append(f"| {atk} | {np.mean(accs):.4f} |")
    out.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=None, help="directory of test images")
    ap.add_argument("--delta", type=float, default=16.0)
    ap.add_argument("--payload", type=int, default=64)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--tag", type=str, default="default")
    args = ap.parse_args()

    cfg = DCTWatermarkConfig(delta=args.delta, seed=args.seed, payload_bits=args.payload)
    images = _load_batch(args.dir) if args.dir else _synthetic_batch()

    csv_path = run(cfg, images, args.tag)
    print(f"wrote {csv_path}")
    print(f"wrote {csv_path.with_suffix('.md').as_posix().replace('.csv', '.md')}")


if __name__ == "__main__":
    main()
