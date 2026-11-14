"""Corrected evaluation v3 (historical module name retained).

Protocol (fixes every v1 flaw listed in FINDINGS.md):
  * Deduplicated real crops, 5 content-checked folds grouped by source.
  * Embedder CDFs and the attacker's natural reference are fitted on the
    training sources of each fold only; test sources are never seen.
  * Both methods embed at the SAME DCT position (default (3,3)).
  * Fidelity-robustness curves: DP-QIM swept over safety margin, DCT-QIM
    swept over Delta; comparisons are made at matched PSNR by interpolating
    the baseline curve.
  * The UnMarker-style attacker uses full natural coefficient histograms
    from training sources — never the embedder's sample pools.
  * Payload seeds use crc32; CIs are a source-level bootstrap.

Usage:
  python -m experiments.eval_v2 curves   # robustness vs PSNR (+ UnMarker)
  python -m experiments.eval_v2 detect   # learned-detector AUC vs payload
  python -m experiments.eval_v2 report   # tables from saved records
"""
from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.attacks import AttackSuite
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import decode as qim_decode
from src.dct_watermark import encode as qim_encode
from src.dp_qim_watermark import DPQIMConfig
from src.dp_qim_watermark import decode as dp_decode
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import bit_accuracy, psnr
from src.natural_cdf import fit_natural_cdfs
from src.protocol import block_dct, bootstrap_ci, real_crops, source_folds, stable_seed, provenance
from src.unmarker_attack import UnMarkerConfig, attack as unmarker_attack

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "v3"

DP_MARGINS = (0.5, 1.0, 2.0, 3.0, 4.0, 6.0)
# Extends to large steps so the baseline curve spans DP-QIM's PSNR range
# (interpolation must never clamp at the end of the sweep).
QIM_DELTAS = (6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 128)
UNMARKER_SETTINGS = ((2.0, 0.5), (2.0, 1.0), (1.5, 1.0))
ROBUST = ("jpeg_q90", "jpeg_q70", "gauss_blur_1.0", "gauss_noise_.03", "resize_0.5",
          "contrast_0.5", "contrast_0.8", "contrast_1.2")


def _contrast(s):
    """Valumetric scaling about the image mean: scales every AC DCT coefficient by s."""
    def _apply(rgb):
        x = rgb.astype(np.float32)
        return np.clip(np.round(x.mean() + s * (x - x.mean())), 0, 255).astype(np.uint8)
    return _apply


EXTRA_ATTACKS = (("contrast_0.5", _contrast(0.5)), ("contrast_0.8", _contrast(0.8)),
                 ("contrast_1.2", _contrast(1.2)))


def _attacker_reference(train_crops) -> dict:
    coeffs = np.concatenate([block_dct(c.image) for c in train_crops])
    return {(u, v): coeffs[:, u, v].copy()
            for u in range(8) for v in range(8) if (u, v) != (0, 0)}


def _evaluate(method, param, encode, decode, cfg, crop, suite, attacker_ref, payload):
    bits = (np.random.default_rng(stable_seed(crop.name)).integers(0, 2, payload)
            .astype(np.uint8))
    wm = encode(crop.image, bits, cfg)
    rec = {"method": method, "param": param, "payload": payload,
           "source": crop.source, "crop": crop.name, "psnr": psnr(crop.image, wm)}
    for name, atk in tuple(suite.attacks) + EXTRA_ATTACKS:
        rec[name] = bit_accuracy(bits, decode(atk(wm), cfg))
    for thr, jit in UNMARKER_SETTINGS:
        ucfg = UnMarkerConfig(attacker_reference=attacker_ref, peak_ratio_threshold=thr,
                              jitter_scale=jit, seed=stable_seed(crop.name) ^ 7)
        attacked = unmarker_attack(wm, ucfg)
        key = f"unmarker_t{thr}_j{jit}"
        rec[key] = bit_accuracy(bits, decode(attacked, cfg))
        rec[key + "_psnr"] = psnr(wm, attacked)
    return rec


def run_curves(uv, payload, out_path):
    if out_path.exists():
        raise FileExistsError("Preserve completed results; choose a new output path")
    crops = real_crops()
    suite = AttackSuite.default()
    records = []
    t0 = time.time()
    for fold, (train, test) in enumerate(source_folds(crops)):
        train_coeffs = np.concatenate([block_dct(c.image) for c in train])
        attacker_ref = _attacker_reference(train)
        for sm in DP_MARGINS:
            cdfs = fit_natural_cdfs(train_coeffs, m=1, safety_margin=sm,
                                    max_pool_size=512, positions=(uv,))
            cfg = DPQIMConfig(seed=1337, payload_bits=payload, uv=uv, cdfs=cdfs)
            for crop in test:
                r = _evaluate("DP-QIM", sm, dp_encode, dp_decode, cfg, crop,
                              suite, attacker_ref, payload)
                r["fold"] = fold
                records.append(r)
        for d in QIM_DELTAS:
            cfg = DCTWatermarkConfig(delta=d, seed=1337, payload_bits=payload, uv=uv)
            for crop in test:
                r = _evaluate("DCT-QIM", d, qim_encode, qim_decode, cfg, crop,
                              suite, attacker_ref, payload)
                r["fold"] = fold
                records.append(r)
        print(f"fold {fold} done  ({time.time() - t0:.0f}s, {len(records)} records)", flush=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"uv": list(uv), "payload": payload, "provenance": provenance(crops),
                                    "records": records}, indent=1))
    print(f"wrote {out_path}")


# ---------------------------------------------------------------- analysis

def _curve(records, method, metric, sources=None):
    """Return sorted arrays (param, mean_psnr, mean_metric) for one method."""
    by_param = defaultdict(lambda: ([], []))
    for r in records:
        if r["method"] != method or (sources is not None and r["source"] not in sources):
            continue
        by_param[r["param"]][0].append(r["psnr"])
        by_param[r["param"]][1].append(r[metric])
    params = sorted(by_param)
    return (np.array(params),
            np.array([np.mean(by_param[p][0]) for p in params]),
            np.array([np.mean(by_param[p][1]) for p in params]))


def _interp_at_psnr(psnrs, values, target):
    order = np.argsort(psnrs)
    p = psnrs[order]
    if not (p[0] <= target <= p[-1]):
        raise ValueError(f"PSNR {target:.2f} outside baseline sweep [{p[0]:.2f}, {p[-1]:.2f}]")
    return float(np.interp(target, p, values[order]))


def matched_gain(records, dp_param, metric, n_boot=2000, seed=0):
    """DP-QIM minus PSNR-matched DCT-QIM, with a source-bootstrap 95% CI."""
    sources = sorted({r["source"] for r in records})

    def stat(src_list):
        multiset = defaultdict(int)
        for s in src_list:
            multiset[s] += 1
        sub = [r for r in records for _ in range(multiset.get(r["source"], 0))]
        dp = [r for r in sub if r["method"] == "DP-QIM" and r["param"] == dp_param]
        dp_psnr = np.mean([r["psnr"] for r in dp])
        dp_val = np.mean([r[metric] for r in dp])
        _, q_psnr, q_val = _curve(sub, "DCT-QIM", metric)
        return dp_val - _interp_at_psnr(q_psnr, q_val, dp_psnr), dp_psnr, dp_val

    point, dp_psnr, dp_val = stat(sources)
    rng = np.random.default_rng(seed)
    boots, skipped = [], 0
    for _ in range(n_boot):
        try:
            boots.append(stat([sources[i] for i in rng.integers(0, len(sources), len(sources))])[0])
        except ValueError:      # resample's PSNR fell outside the baseline sweep
            skipped += 1
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return {"gain": point, "lo": float(lo), "hi": float(hi), "skipped": skipped,
            "dp_psnr": float(dp_psnr), "dp_value": float(dp_val)}


def report_curves(path):
    data = json.loads(Path(path).read_text())
    recs, uv, payload = data["records"], tuple(data["uv"]), data["payload"]
    metrics = (["identity"] + list(ROBUST) +
               [f"unmarker_t{t}_j{j}" for t, j in UNMARKER_SETTINGS])
    lines = [f"# v2 robustness at matched PSNR — uv={uv}, payload={payload}",
             "",
             f"{len({r['crop'] for r in recs})} test crops from "
             f"{len({r['source'] for r in recs})} sources, 5 source-grouped folds. "
             "Gain = DP-QIM minus DCT-QIM interpolated to the same mean PSNR; "
             "95% CI from a source-level bootstrap.",
             ""]
    q_min = min(np.mean([r["psnr"] for r in recs if r["method"] == "DCT-QIM" and r["param"] == d])
                for d in {r["param"] for r in recs if r["method"] == "DCT-QIM"})
    for sm in DP_MARGINS:
        dp_ps = np.mean([r["psnr"] for r in recs if r["method"] == "DP-QIM" and r["param"] == sm])
        if dp_ps < q_min + 1.0:
            lines += [f"## DP-QIM safety margin {sm} (mean PSNR {dp_ps:.2f} dB)", "",
                      "Outside the baseline sweep's PSNR range (bootstrap resamples "
                      "would extrapolate); not compared.", ""]
            continue
        rows = []
        for m in metrics:
            g = matched_gain(recs, sm, m, n_boot=500)
            rows.append((m, g))
        ps = rows[0][1]["dp_psnr"]
        lines += [f"## DP-QIM safety margin {sm} (mean PSNR {ps:.2f} dB)", "",
                  "| metric | DP-QIM | gain vs matched DCT-QIM (pp) | 95% CI |",
                  "|---|---|---|---|"]
        for m, g in rows:
            sig = " *" if g["lo"] > 0 or g["hi"] < 0 else ""
            lines.append(f"| {m} | {g['dp_value']:.3f} | {100*g['gain']:+.1f}{sig} | "
                         f"[{100*g['lo']:+.1f}, {100*g['hi']:+.1f}] |")
        lines.append("")
    lines += ["## DCT-QIM curve", "", "| Delta | PSNR | identity | " +
              " | ".join(metrics[1:]) + " |", "|" + "---|" * (len(metrics) + 2)]
    for d in QIM_DELTAS:
        rs = [r for r in recs if r["method"] == "DCT-QIM" and r["param"] == d]
        if not rs:
            continue
        cells = " | ".join(f"{np.mean([r[m] for r in rs]):.3f}" for m in metrics)
        lines.append(f"| {d} | {np.mean([r['psnr'] for r in rs]):.2f} | {cells} |")
    lines += ["", "## DP-QIM curve", "", "| margin | PSNR | identity | " +
              " | ".join(metrics[1:]) + " |", "|" + "---|" * (len(metrics) + 2)]
    for sm in DP_MARGINS:
        rs = [r for r in recs if r["method"] == "DP-QIM" and r["param"] == sm]
        cells = " | ".join(f"{np.mean([r[m] for r in rs]):.3f}" for m in metrics)
        lines.append(f"| {sm} | {np.mean([r['psnr'] for r in rs]):.2f} | {cells} |")
    out = Path(path).with_suffix(".md")
    out.write_text("\n".join(lines) + "\n")
    print(out.read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["curves", "report"])
    ap.add_argument("--uv", nargs=2, type=int, default=(3, 3))
    ap.add_argument("--payload", type=int, default=64)
    args = ap.parse_args()
    uv = tuple(args.uv)
    path = OUT / f"curves_uv{uv[0]}{uv[1]}_p{args.payload}.json"
    if args.cmd == "curves":
        run_curves(uv, args.payload, path)
        report_curves(path)
    else:
        report_curves(path)


if __name__ == "__main__":
    main()
