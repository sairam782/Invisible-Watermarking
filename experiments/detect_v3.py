"""Inductive detector evaluation with one content-checked outer source split.

Every fitted component (CDF, QIM fidelity calibration, scaler, classifier,
and peak reference) sees outer-training sources only. AUC is computed within
each fold, then averaged with test-crop weights, never by comparing raw
decision scores from separately fitted classifiers. Source bootstrap CIs
are conditional on these fitted models and this fixed split.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.dct_watermark import DCTWatermarkConfig, encode as qim_encode
from src.dp_qim_watermark import DPQIMConfig, encode as dp_encode
from src.metrics import psnr
from src.natural_cdf import fit_natural_cdfs
from src.protocol import (assert_disjoint, block_dct, provenance, real_crops,
                          source_folds, stable_seed)

OUT = Path(__file__).resolve().parent.parent / "results" / "v3"
UV = (3, 3)
PAYLOADS = (64, 256, 1024)
DP_MARGINS = (1.0, 2.0)
QIM_DELTAS = tuple(range(4, 66, 2))
BINS = np.arange(-48.5, 49.5, 1.0)


def _bits(name, n):
    return np.random.default_rng(stable_seed(name)).integers(0, 2, n).astype(np.uint8)


def _hist(img):
    c = block_dct(img)[:, UV[0], UV[1]]
    return np.histogram(np.clip(c, -48, 48), bins=BINS)[0] / c.size


def _peak_score(img, reference):
    edges = np.linspace(-48, 48, 65)
    c = block_dct(img)[:, UV[0], UV[1]]
    p = np.histogram(np.clip(c, -48, 48), bins=edges)[0]
    q = np.histogram(np.clip(reference, -48, 48), bins=edges)[0]
    return float(np.max((p / p.sum()) / np.maximum(q / q.sum(), 1e-4)))


def _encode(crops, fn, cfg, payload):
    return {c.name: fn(c.image, _bits(c.name, payload), cfg) for c in crops}


def fit_fold(train, payload, margin):
    """Accept training crops only: no test-based fidelity or model selection."""
    coeffs = np.concatenate([block_dct(c.image) for c in train])
    cdfs = fit_natural_cdfs(coeffs, m=1, safety_margin=margin, positions=(UV,))
    dp_cfg = DPQIMConfig(seed=1337, payload_bits=payload, uv=UV, cdfs=cdfs)
    dp_train = _encode(train, dp_encode, dp_cfg, payload)
    target = float(np.mean([psnr(c.image, dp_train[c.name]) for c in train]))
    best = None
    for delta in QIM_DELTAS:
        cfg = DCTWatermarkConfig(delta=delta, seed=1337, payload_bits=payload, uv=UV)
        encoded = _encode(train, qim_encode, cfg, payload)
        fidelity = float(np.mean([psnr(c.image, encoded[c.name]) for c in train]))
        if best is None or abs(fidelity - target) < best[0]:
            best = abs(fidelity - target), cfg, encoded, fidelity
    _, q_cfg, q_train, q_psnr = best
    audit = {"train_sources": sorted({c.source for c in train}),
             "cdf_boundary": float(cdfs[UV].edges[1]),
             "qim_delta": q_cfg.delta, "dp_train_psnr": target,
             "qim_train_psnr": q_psnr}
    return dp_cfg, q_cfg, dp_train, q_train, coeffs[:, UV[0], UV[1]], audit


def fold_weighted_auc(y, scores, folds):
    """Weighted mean within-fold AUC; invariant to monotone fold rescaling."""
    y, scores, folds = map(np.asarray, (y, scores, folds))
    aucs, weights = [], []
    for fold in np.unique(folds):
        idx = folds == fold
        yy, ss = y[idx], scores[idx]
        pos = yy == 1
        n1, n0 = int(pos.sum()), int((~pos).sum())
        if not n1 or not n0:
            raise ValueError("Each represented fold must contain both labels")
        auc = (rankdata(ss)[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        aucs.append(auc)
        weights.append(len(yy))
    return float(np.average(aucs, weights=weights))


def auc_with_ci(records, n_boot=2000, seed=0):
    y = np.array([r["label"] for r in records])
    scores = np.array([r["score"] for r in records])
    folds = np.array([r["fold"] for r in records])
    sources = np.array([r["source"] for r in records])
    names = np.unique(sources)
    indices = {s: np.where(sources == s)[0] for s in names}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        ix = np.concatenate([indices[s] for s in rng.choice(names, len(names))])
        boots.append(fold_weighted_auc(y[ix], scores[ix], folds[ix]))
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return fold_weighted_auc(y, scores, folds), float(lo), float(hi)


def evaluate_setting(crops, payload, margin):
    scores, audits, fidelities = [], [], []
    for fold, (train, test) in enumerate(source_folds(crops)):
        assert_disjoint(train, test)
        dc, qc, dt, qt, ref, audit = fit_fold(train, payload, margin)
        de, qe = _encode(test, dp_encode, dc, payload), _encode(test, qim_encode, qc, payload)
        audit.update(fold=fold, test_sources=sorted({c.source for c in test}))
        audit["dp_test_psnr"] = float(np.mean([psnr(c.image, de[c.name]) for c in test]))
        audit["qim_test_psnr"] = float(np.mean([psnr(c.image, qe[c.name]) for c in test]))
        audits.append(audit)
        fidelities += [{"crop": c.name, "dp": psnr(c.image, de[c.name]),
                        "qim": psnr(c.image, qe[c.name])} for c in test]
        for tag, train_stego, test_stego in (("dp", dt, de), ("qim", qt, qe)):
            X = np.array([_hist(c.image) for c in train] + [_hist(train_stego[c.name]) for c in train])
            y = np.array([0] * len(train) + [1] * len(train))
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))
            clf.fit(X, y)
            for c in test:
                for label, img in ((0, c.image), (1, test_stego[c.name])):
                    for detector, value in (("learned", float(clf.decision_function([_hist(img)])[0])),
                                            ("peak", _peak_score(img, ref))):
                        scores.append({"payload": payload, "margin": margin, "fold": fold,
                                       "source": c.source, "crop": c.name, "method": tag,
                                       "detector": detector, "label": label, "score": value})
        print(f"payload={payload} margin={margin} fold={fold} delta={qc.delta}", flush=True)
    row = {"payload": payload, "dp_margin": margin,
           "qim_delta": [a["qim_delta"] for a in audits],
           "dp_psnr": float(np.mean([r["dp"] for r in fidelities])),
           "qim_psnr": float(np.mean([r["qim"] for r in fidelities])),
           "auc_aggregation": "test-crop-weighted within-fold AUC",
           "ci_scope": "source bootstrap conditional on fitted models and fixed split"}
    for tag in ("dp", "qim"):
        for detector in ("learned", "peak"):
            selected = [r for r in scores if r["method"] == tag and r["detector"] == detector]
            value, lo, hi = auc_with_ci(selected)
            row[f"{tag}_auc_{detector}"] = value
            row[f"{tag}_auc_{detector}_ci"] = [lo, hi]
    return row, scores, audits


def _stego_sets(crops, payload, margin):
    """Held-out examples for the figure, using training-only fold calibration."""
    dp, qim, deltas = {}, {}, []
    for train, test in source_folds(crops):
        dc, qc, _, _, _, _ = fit_fold(train, payload, margin)
        dp.update(_encode(test, dp_encode, dc, payload))
        qim.update(_encode(test, qim_encode, qc, payload))
        deltas.append(qc.delta)
    dps = float(np.mean([psnr(c.image, dp[c.name]) for c in crops]))
    qs = float(np.mean([psnr(c.image, qim[c.name]) for c in crops]))
    return dp, dps, ("fold-calibrated", qim, qs)


def main():
    if (OUT / "detect.json").exists():
        raise FileExistsError("Preserve completed results before rerunning")
    OUT.mkdir(parents=True, exist_ok=True)
    crops = real_crops()
    rows, all_scores, all_audits = [], [], []
    for payload in PAYLOADS:
        for margin in DP_MARGINS:
            row, scores, audits = evaluate_setting(crops, payload, margin)
            rows.append(row)
            all_scores.extend(scores)
            all_audits.append({"payload": payload, "margin": margin, "folds": audits})
            (OUT / "detect.partial.json").write_text(json.dumps(rows, indent=2))
            print(json.dumps(row), flush=True)
    (OUT / "detect.json").write_text(json.dumps(rows, indent=2) + "\n")
    (OUT / "detect_scores.jsonl").write_text("".join(json.dumps(r) + "\n" for r in all_scores))
    (OUT / "detect_audit.json").write_text(json.dumps({"provenance": provenance(crops),
                                                     "settings": all_audits}, indent=2) + "\n")
    lines = ["# Corrected v3 detectability", "",
             "43 crops / 14 sources; training-only outer-fold fitting and fidelity calibration.",
             "AUC: test-crop-weighted mean within-fold AUC; conditional source-bootstrap CIs.", "",
             "| Bits | Margin | DP PSNR | QIM PSNR | DP learned AUC | QIM learned AUC | DP peak | QIM peak |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        keys = ["payload", "dp_margin", "dp_psnr", "qim_psnr", "dp_auc_learned",
                "qim_auc_learned", "dp_auc_peak", "qim_auc_peak"]
        lines.append("| " + " | ".join(f"{r[k]:.3f}" for k in keys) + " |")
    (OUT / "detect.md").write_text("\n".join(lines) + "\n")
    (OUT / "detect.partial.json").unlink()


if __name__ == "__main__":
    main()
