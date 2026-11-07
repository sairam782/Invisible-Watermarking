"""Detectability v2: can a steganalysis-style detector tell stego from cover?

Replaces the v1 per-image KS statistic (n=64 samples; its null distribution
already has mean ~0.11, so v1 KS differences were noise) with two detectors
evaluated by ROC-AUC (0.5 = undetectable, 1.0 = perfectly detectable):

  * learned:  logistic regression on the fine histogram of the embedding
              position's coefficient over ALL blocks of the image. The
              detector knows the scheme and position (Kerckhoffs) but not
              the key, so it cannot tell which blocks carry payload.
  * peak:     the UnMarker statistic itself, unsupervised — maximum
              over-density of the image's histogram relative to a natural
              reference built from other sources' cover images.

Both are evaluated with folds grouped by source photo. Payload density is
swept from 64 bits (6% of blocks) to 1024 bits (every block of a 256x256
crop). DCT-QIM's step is chosen so its mean PSNR matches DP-QIM's at each
payload.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import encode as qim_encode
from src.dp_qim_watermark import DPQIMConfig
from src.dp_qim_watermark import encode as dp_encode
from src.metrics import psnr
from src.natural_cdf import fit_natural_cdfs
from src.protocol import block_dct, real_crops, source_folds, stable_seed

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "v2"

UV = (3, 3)
PAYLOADS = (64, 256, 1024)
DP_MARGINS = (1.0, 2.0)
QIM_DELTAS = tuple(range(4, 66, 2))
BINS = np.arange(-48.5, 49.5, 1.0)


def _hist(img):
    c = block_dct(img)[:, UV[0], UV[1]]
    h, _ = np.histogram(np.clip(c, -48, 48), bins=BINS)
    return h / max(c.size, 1)


def _peak_score(img, reference):
    c = block_dct(img)[:, UV[0], UV[1]]
    edges = np.linspace(-48, 48, 65)
    p, _ = np.histogram(np.clip(c, -48, 48), bins=edges)
    q, _ = np.histogram(np.clip(reference, -48, 48), bins=edges)
    p = p / p.sum()
    q = np.maximum(q / q.sum(), 1e-4)
    return float(np.max(p / q))


def _bits(name, n):
    return np.random.default_rng(stable_seed(name)).integers(0, 2, n).astype(np.uint8)


def _stego_sets(crops, payload, margin):
    """DP-QIM stego for every crop (CDF fitted without the crop's source), and
    DCT-QIM stego at the Delta whose mean PSNR is closest to DP-QIM's."""
    dp = {}
    for train, test in source_folds(crops):
        coeffs = np.concatenate([block_dct(c.image) for c in train])
        cdfs = fit_natural_cdfs(coeffs, m=1, safety_margin=margin, positions=(UV,))
        cfg = DPQIMConfig(seed=1337, payload_bits=payload, uv=UV, cdfs=cdfs)
        for c in test:
            dp[c.name] = dp_encode(c.image, _bits(c.name, payload), cfg)
    dp_psnr = float(np.mean([psnr(c.image, dp[c.name]) for c in crops]))

    best = None
    for d in QIM_DELTAS:
        cfg = DCTWatermarkConfig(delta=d, seed=1337, payload_bits=payload, uv=UV)
        q = {c.name: qim_encode(c.image, _bits(c.name, payload), cfg) for c in crops}
        q_psnr = float(np.mean([psnr(c.image, q[c.name]) for c in crops]))
        if best is None or abs(q_psnr - dp_psnr) < abs(best[2] - dp_psnr):
            best = (d, q, q_psnr)
    return dp, dp_psnr, best


def _auc_with_ci(y, scores, groups, n_boot=2000, seed=0):
    """AUC of out-of-fold scores, with a 95% CI from resampling whole sources."""
    y, scores, groups = map(np.asarray, (y, scores, groups))
    point = float(roc_auc_score(y, scores))
    srcs = np.unique(groups)
    idx_by_src = {s: np.where(groups == s)[0] for s in srcs}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = np.concatenate([idx_by_src[s] for s in rng.choice(srcs, len(srcs))])
        if len(np.unique(y[idx])) == 2:
            boots.append(roc_auc_score(y[idx], scores[idx]))
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return point, float(lo), float(hi)


def _auc_learned(crops, stego):
    X = np.array([_hist(c.image) for c in crops] + [_hist(stego[c.name]) for c in crops])
    y = np.array([0] * len(crops) + [1] * len(crops))
    groups = np.array([c.source for c in crops] * 2)
    scores = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(X, y, groups):
        clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))
        clf.fit(X[tr], y[tr])
        scores[te] = clf.decision_function(X[te])
    return _auc_with_ci(y, scores, groups)


def _auc_peak(crops, stego):
    scores, y, groups = [], [], []
    for c in crops:
        ref = np.concatenate([block_dct(o.image)[:, UV[0], UV[1]]
                              for o in crops if o.source != c.source])
        scores += [_peak_score(c.image, ref), _peak_score(stego[c.name], ref)]
        y += [0, 1]
        groups += [c.source, c.source]
    return _auc_with_ci(y, scores, groups)


def main():
    crops = real_crops()
    rows = []
    for payload in PAYLOADS:
        for margin in DP_MARGINS:
            dp, dp_psnr, (delta, q, q_psnr) = _stego_sets(crops, payload, margin)
            row = {"payload": payload, "dp_margin": margin, "qim_delta": delta,
                   "dp_psnr": dp_psnr, "qim_psnr": q_psnr}
            for tag, stego in (("dp", dp), ("qim", q)):
                for det, fn in (("learned", _auc_learned), ("peak", _auc_peak)):
                    auc, lo, hi = fn(crops, stego)
                    row[f"{tag}_auc_{det}"] = auc
                    row[f"{tag}_auc_{det}_ci"] = [lo, hi]
            rows.append(row)
            print(f"payload={payload} margin={margin}: "
                  f"learned DP {row['dp_auc_learned']:.3f} vs QIM {row['qim_auc_learned']:.3f}; "
                  f"peak DP {row['dp_auc_peak']:.3f} vs QIM {row['qim_auc_peak']:.3f}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "detect.json").write_text(json.dumps(rows, indent=1))

    def fmt(r, key):
        lo, hi = r[key + "_ci"]
        return f"{r[key]:.2f} [{lo:.2f}, {hi:.2f}]"

    lines = ["# v2 detectability (ROC-AUC, 95% source-bootstrap CI; 0.5 = undetectable)", "",
             f"{len(crops)} real crops, {len({c.source for c in crops})} sources, "
             f"embedding position {UV}, folds grouped by source.", "",
             "| payload | DP margin | DP PSNR | QIM Delta | QIM PSNR | "
             "learned AUC DP | learned AUC QIM | peak AUC DP | peak AUC QIM |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['payload']} | {r['dp_margin']} | {r['dp_psnr']:.2f} | "
                     f"{r['qim_delta']} | {r['qim_psnr']:.2f} | "
                     f"{fmt(r, 'dp_auc_learned')} | {fmt(r, 'qim_auc_learned')} | "
                     f"{fmt(r, 'dp_auc_peak')} | {fmt(r, 'qim_auc_peak')} |")
    (OUT / "detect.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
