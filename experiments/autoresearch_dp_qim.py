"""Autoresearch loop for DP-QIM hyperparameter search.

Pattern inspired by karpathy/autoresearch but targeted at OUR research problem.
The agent mutates DP-QIM hyperparameters, runs the KS + attack-suite scorer,
and tracks a Pareto frontier of (undetectability, robustness, fidelity).

Search space:
    uv              : (2,2) (2,3) (3,2) (3,3) (3,4) (4,3) (4,4)
    m               : 1, 2, 4
    safety_margin   : [1.0, 10.0]
    max_pool_size   : 64 | 128 | 256 | 512 | 1024
    seed            : fixed (determinism)

Objective (composite scalar + Pareto frontier):
    mean_robust_acc : mean bit-acc across {jpeg_q90, gauss_blur_1.0,
                      gauss_noise_.03, resize_0.5}
    ks_distance    : KS vs natural on watermarked coefficients only
    psnr           : fidelity constraint (reject if < min_psnr)

A candidate is kept only if it Pareto-dominates something already in the
leaderboard OR extends the frontier. Scalar hill-climbing uses:
    score = mean_robust_acc - 2.0 * ks_distance   (constrained by psnr >= 60)

Leaderboard persists to results/dpqim_autoresearch_leaderboard.json;
run with --resume to continue.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass, asdict, replace
from pathlib import Path

import numpy as np
from scipy import stats

from src.attacks import AttackSuite
from src.dp_qim_watermark import DPQIMConfig as DPQIMEncCfg
from src.dp_qim_watermark import _block_order, _dct2
from src.dp_qim_watermark import decode as dp_decode
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import bit_accuracy, psnr, ssim
from src.natural_cdf import BLOCK, collect_dct_coeffs, fit_natural_cdfs
from src.utils import block_view, pad_to_multiple, random_bits, rgb_to_ycbcr


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS = REPO_ROOT / "results"

UV_CANDIDATES = [(2, 2), (2, 3), (3, 2), (3, 3), (3, 4), (4, 3), (4, 4)]
M_CANDIDATES = [1, 2, 4]
POOL_CANDIDATES = [64, 128, 256, 512, 1024]

ROBUST_ATTACKS = ("jpeg_q90", "gauss_blur_1.0", "gauss_noise_.03", "resize_0.5")
MIN_PSNR = 60.0


@dataclass(frozen=True)
class SearchConfig:
    """One point in the search space."""
    uv: tuple[int, int]
    m: int
    safety_margin: float
    max_pool_size: int

    def key(self) -> str:
        """Canonical string key for dedup."""
        return (f"uv{self.uv[0]}_{self.uv[1]}_m{self.m}_"
                f"sm{self.safety_margin:.2f}_pool{self.max_pool_size}")


def _photo(seed: int, h: int = 256, w: int = 256) -> np.ndarray:
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


def score_candidate(
    cfg: SearchConfig,
    train_coeffs: np.ndarray,
    test_imgs: list[tuple[str, np.ndarray]],
    natural_bank_per_uv: dict,
    suite: AttackSuite,
    payload_bits: int = 64,
) -> dict:
    """Return metrics dict for one candidate."""
    cdfs = fit_natural_cdfs(
        train_coeffs,
        m=cfg.m,
        safety_margin=cfg.safety_margin,
        max_pool_size=cfg.max_pool_size,
    )
    if cfg.uv not in cdfs:
        return {"error": "no_cdf", "psnr": 0, "ssim": 0, "ks": 1.0,
                "per_attack": {}, "mean_robust_acc": 0.0, "accepted": False}

    enc_cfg = DPQIMEncCfg(
        seed=1337, payload_bits=payload_bits, uv=cfg.uv, cdfs=cdfs,
    )
    per_atk = {a[0]: [] for a in suite.attacks}
    psnrs, ssims, kss = [], [], []
    natural_ref = natural_bank_per_uv[cfg.uv]

    for name, img in test_imgs:
        bits = random_bits(payload_bits, seed=hash(name) & 0xFFFF)
        try:
            wm = dp_encode(img, bits, enc_cfg)
        except Exception as e:
            return {"error": f"encode_failed: {e}", "psnr": 0, "ssim": 0,
                    "ks": 1.0, "per_attack": {}, "mean_robust_acc": 0.0,
                    "accepted": False}
        psnrs.append(psnr(img, wm))
        ssims.append(ssim(img, wm))
        wm_coeffs = _extract_watermarked_coeffs(wm, cfg.uv, payload_bits, 1337)
        kss.append(float(stats.ks_2samp(wm_coeffs, natural_ref).statistic))
        for a_name, atk in suite.attacks:
            per_atk[a_name].append(bit_accuracy(bits, dp_decode(atk(wm), enc_cfg)))

    mean_psnr = float(np.mean(psnrs))
    mean_ssim = float(np.mean(ssims))
    mean_ks = float(np.mean(kss))
    per_atk_mean = {k: float(np.mean(v)) for k, v in per_atk.items()}
    mean_robust = float(np.mean([per_atk_mean[a] for a in ROBUST_ATTACKS]))

    accepted = mean_psnr >= MIN_PSNR
    scalar = mean_robust - 2.0 * mean_ks if accepted else -1.0

    return {
        "error": None,
        "psnr": mean_psnr,
        "ssim": mean_ssim,
        "ks": mean_ks,
        "per_attack": per_atk_mean,
        "mean_robust_acc": mean_robust,
        "scalar_score": scalar,
        "accepted": accepted,
    }


def random_config(rng: random.Random) -> SearchConfig:
    return SearchConfig(
        uv=rng.choice(UV_CANDIDATES),
        m=rng.choice(M_CANDIDATES),
        safety_margin=round(rng.uniform(1.0, 10.0), 2),
        max_pool_size=rng.choice(POOL_CANDIDATES),
    )


def mutate_config(cfg: SearchConfig, rng: random.Random) -> SearchConfig:
    """Perturb one or two dimensions of cfg."""
    dims = rng.sample(["uv", "m", "safety_margin", "max_pool_size"],
                       k=rng.randint(1, 2))
    changes: dict = {}
    if "uv" in dims:
        changes["uv"] = rng.choice([u for u in UV_CANDIDATES if u != cfg.uv])
    if "m" in dims:
        changes["m"] = rng.choice([m for m in M_CANDIDATES if m != cfg.m])
    if "safety_margin" in dims:
        step = rng.uniform(-2.0, 2.0)
        new_sm = max(0.5, min(10.0, cfg.safety_margin + step))
        changes["safety_margin"] = round(new_sm, 2)
    if "max_pool_size" in dims:
        changes["max_pool_size"] = rng.choice(
            [p for p in POOL_CANDIDATES if p != cfg.max_pool_size]
        )
    return replace(cfg, **changes)


def dominates(a: dict, b: dict) -> bool:
    """Pareto-dominates: a is at least as good on every objective and strictly better on one.

    Objectives: maximize mean_robust_acc, minimize ks, maximize psnr.
    """
    if not a.get("accepted") or not b.get("accepted"):
        return a.get("accepted") and not b.get("accepted")
    better = False
    if a["mean_robust_acc"] < b["mean_robust_acc"]:
        return False
    if a["mean_robust_acc"] > b["mean_robust_acc"]:
        better = True
    if a["ks"] > b["ks"]:
        return False
    if a["ks"] < b["ks"]:
        better = True
    if a["psnr"] < b["psnr"] - 0.5:   # 0.5 dB tolerance to avoid noise
        return False
    if a["psnr"] > b["psnr"] + 0.5:
        better = True
    return better


def update_pareto(frontier: list[dict], candidate: dict) -> list[dict]:
    """Insert candidate into frontier, pruning dominated entries."""
    if not candidate.get("accepted"):
        return frontier
    pruned = [f for f in frontier if not dominates(candidate, f)]
    if any(dominates(f, candidate) for f in pruned):
        return pruned
    pruned.append(candidate)
    return pruned


def save_state(state: dict, path: Path) -> None:
    path.write_text(json.dumps(state, indent=2, default=str))


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"history": [], "frontier": [], "best_scalar": None, "n_trials": 0}
    return json.loads(path.read_text())


def write_leaderboard_md(state: dict, out_md: Path) -> None:
    history = state["history"]
    frontier = state["frontier"]
    lines = [
        "# DP-QIM autoresearch leaderboard",
        "",
        f"Trials completed: **{state['n_trials']}**  ·  Frontier size: **{len(frontier)}**",
        "",
        "## Best scalar score (mean_robust_acc - 2·KS)",
        "",
    ]
    accepted = [h for h in history if h.get("accepted")]
    if accepted:
        best = max(accepted, key=lambda h: h["scalar_score"])
        lines += [
            f"- Score: **{best['scalar_score']:.4f}**",
            f"- Config: `{best['config_key']}`",
            f"- Mean robust acc: **{best['mean_robust_acc']:.3f}**",
            f"- KS vs natural: **{best['ks']:.4f}**",
            f"- PSNR: **{best['psnr']:.2f}** dB  ·  SSIM: {best['ssim']:.4f}",
            "",
        ]

    lines += ["## Pareto frontier (sorted by robustness)", "",
              "| config | PSNR | KS | robust_acc | " + " | ".join(ROBUST_ATTACKS) + " |",
              "|---|---|---|---|" + "|".join(["---"] * len(ROBUST_ATTACKS)) + "|"]
    for f in sorted(frontier, key=lambda f: -f["mean_robust_acc"]):
        atks = " | ".join(f"{f['per_attack'].get(a, 0):.3f}" for a in ROBUST_ATTACKS)
        lines.append(
            f"| `{f['config_key']}` | {f['psnr']:.2f} | {f['ks']:.4f} | "
            f"{f['mean_robust_acc']:.3f} | {atks} |"
        )

    out_md.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget-minutes", type=float, default=10.0)
    ap.add_argument("--max-trials", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--state", type=Path,
                    default=RESULTS / "dpqim_autoresearch_leaderboard.json")
    args = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    print("preparing training coefficients + test photos + natural reference...")
    train_imgs = [_photo(i) for i in range(16)]
    train_coeffs = collect_dct_coeffs(train_imgs)
    test_imgs = [(f"test_{i:02d}", _photo(1000 + i)) for i in range(8)]
    natural_ref_imgs = [_photo(2000 + i) for i in range(8)]
    natural_bank_all = collect_dct_coeffs(natural_ref_imgs)
    natural_bank_per_uv = {
        uv: natural_bank_all[..., uv[0], uv[1]].flatten() for uv in UV_CANDIDATES
    }
    suite = AttackSuite.default()

    state = load_state(args.state) if args.resume else {
        "history": [], "frontier": [], "best_scalar": None, "n_trials": 0
    }
    seen_keys = {h["config_key"] for h in state["history"]}
    print(f"starting with {state['n_trials']} trials in state ({len(seen_keys)} seen)")

    rng = random.Random(args.seed + state["n_trials"])
    t_start = time.time()
    current = None
    trial = state["n_trials"]

    while True:
        elapsed = (time.time() - t_start) / 60.0
        if elapsed >= args.budget_minutes:
            print(f"\nbudget reached ({elapsed:.1f} min)")
            break
        if trial - state["n_trials"] >= args.max_trials:
            print(f"\nmax-trials reached ({args.max_trials})")
            break

        if current is None or rng.random() < 0.3:
            cfg = random_config(rng)      # explore
            mode = "random"
        else:
            cfg = mutate_config(current, rng)   # exploit
            mode = "mutate"
        key = cfg.key()
        if key in seen_keys:
            continue
        seen_keys.add(key)

        t_cfg = time.time()
        metrics = score_candidate(cfg, train_coeffs, test_imgs,
                                   natural_bank_per_uv, suite)
        cfg_time = time.time() - t_cfg
        trial += 1

        entry = {
            "trial": trial,
            "mode": mode,
            "config_key": key,
            "config": asdict(cfg),
            "time_sec": round(cfg_time, 2),
            **metrics,
        }
        state["history"].append(entry)
        state["n_trials"] = trial

        acceptance = "✓" if metrics["accepted"] else "✗"
        robust = metrics["mean_robust_acc"] if metrics["accepted"] else 0
        print(f"[{trial:3d}][{mode:6s}][{acceptance}] {key}  "
              f"ks={metrics['ks']:.4f} psnr={metrics['psnr']:.2f} "
              f"robust={robust:.3f} score={metrics.get('scalar_score', -1):.4f} "
              f"({cfg_time:.1f}s)")

        if metrics["accepted"]:
            # Hill climbing: accept as current if it beats scalar score
            if (current is None
                    or metrics["scalar_score"] >
                        max([h.get("scalar_score", -2)
                             for h in state["history"]
                             if h.get("config_key") == current.key()],
                            default=-2)):
                current = cfg
            state["frontier"] = update_pareto(state["frontier"], entry)

        if trial % 5 == 0:
            save_state(state, args.state)

    save_state(state, args.state)
    md_path = args.state.with_suffix(".md")
    write_leaderboard_md(state, md_path)
    print(f"\nwrote {args.state}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
