import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from src.protocol import (Crop, assert_disjoint, deduplicate_sources,
                          image_hash, real_crops, source_folds)
from src.dct_watermark import _qim_decode
from src.natural_cdf import fit_natural_cdfs
from experiments import detect_v3 as det


def crop(name, seed):
    return Crop(name, 0, np.random.default_rng(seed).integers(30, 220, (32, 32, 3), dtype=np.uint8))


def test_alias_deduplication_by_content_not_name():
    a, b = crop("a", 1), crop("b", 2)
    unique, aliases = deduplicate_sources({"original": a.image, "alias": a.image.copy(), "b": b.image})
    assert len(unique) == 2
    assert aliases == {"original": "alias"}


def test_duplicate_content_cannot_cross_split():
    a = crop("a", 1)
    with pytest.raises(ValueError, match="leakage"):
        assert_disjoint([a], [Crop("renamed", 0, a.image.copy())])
    with pytest.raises(ValueError, match="Duplicate"):
        list(source_folds([a, Crop("renamed", 0, a.image.copy())], k=2))


def test_source_folds_cover_each_crop_once():
    crops = [crop(str(i), i) for i in range(8)]
    seen = []
    for train, test in source_folds(crops):
        assert_disjoint(train, test)
        seen.extend(c.name for c in test)
    assert sorted(seen) == sorted(c.name for c in crops)


def test_actual_sources_have_no_alias_or_duplicate_crop():
    crops = real_crops()
    assert len(crops) == 43
    assert len({c.source for c in crops}) == 14
    assert "cat" not in {c.source for c in crops}
    assert len({image_hash(c.image) for c in crops}) == len(crops)
    for train, test in source_folds(crops):
        assert_disjoint(train, test)


def test_qim_scaling_counterexample_to_old_iff_claim():
    c, delta, scale = 32.0, 16.0, 0.5
    assert abs(1 - scale) * abs(c) >= delta / 4
    assert _qim_decode(np.array([c]), delta)[0] == _qim_decode(np.array([scale*c]), delta)[0]


def test_periodic_qim_condition_away_from_ties():
    delta = 16.0
    c = np.arange(-15, 16) * delta / 2
    for scale in (0.13, 0.37, 0.71, 1.11, 2.07):
        displacement = (scale - 1) * c
        distance = np.abs((displacement + delta/2) % delta - delta/2)
        nontie = ~np.isclose(distance, delta/4)
        preserved = _qim_decode(c, delta) == _qim_decode(scale*c, delta)
        np.testing.assert_array_equal(preserved[nontie], (distance < delta/4)[nontie])


def test_safe_cell_mixture_is_not_global_conditioning():
    x = np.array([-4, -3, -2, -1, .1, .2, .3, 10], dtype=np.float32)
    coeffs = np.zeros((len(x), 8, 8), dtype=np.float32)
    coeffs[:, 3, 3] = x
    cdf = fit_natural_cdfs(coeffs, m=1, safety_margin=1, positions=((3, 3),))[(3, 3)]
    assert [len(p) for p in cdf.sample_pools] == [3, 1]
    # Equal-cell replacement has half its mass on each side; global conditioning does not.
    assert len(cdf.sample_pools[0]) / sum(map(len, cdf.sample_pools)) == .75
    assert .5 * .5 + .25 == .5  # idealized watermarked lower-cell mass
    assert .5 * .5 + .5 * .75 == .625  # incorrect old global-mixture prediction

    # Enumerate original value, independent payload bit, and uniform pool draw.
    actual = np.zeros(len(x))
    for i, value in enumerate(x):
        current = int(cdf.cell_index(np.array([value]))[0])
        for bit in (0, 1):
            if current == bit:
                actual[i] += 1 / (2 * len(x))
            else:
                for replacement in cdf.sample_pools[bit]:
                    j = int(np.flatnonzero(x == replacement)[0])
                    actual[j] += 1 / (2 * len(x) * len(cdf.sample_pools[bit]))
    expected = np.full(len(x), .5 / len(x))
    for pool in cdf.sample_pools:
        for replacement in pool:
            expected[int(np.flatnonzero(x == replacement)[0])] += .25 / len(pool)
    np.testing.assert_allclose(actual, expected)


def test_zero_margin_pool_uses_decoder_boundary_convention():
    a = np.zeros((6, 8, 8), dtype=np.float32)
    a[:, 3, 3] = [-2, -1, 0, 0, 1, 2]
    cdf = fit_natural_cdfs(a, m=1, safety_margin=0, positions=((3, 3),))[(3, 3)]
    for i, pool in enumerate(cdf.sample_pools):
        assert np.all(cdf.cell_index(pool) == i)


def test_fold_auc_matches_sklearn_and_ignores_cross_fold_score_scales():
    y = np.array([0, 0, 1, 1] * 2)
    score = np.array([0., 2, 1, 3, 1, 0, 3, 2])
    folds = np.array([0]*4 + [1]*4)
    expected = np.mean([roc_auc_score(y[:4], score[:4]), roc_auc_score(y[4:], score[4:])])
    assert det.fold_weighted_auc(y, score, folds) == expected
    score[4:] = score[4:] * 1000 + 9999
    assert det.fold_weighted_auc(y, score, folds) == expected


def test_heldout_pixels_do_not_change_fitted_parameters(monkeypatch):
    train = [crop(str(i), i) for i in range(4)]
    test = [crop("heldout", 9)]
    monkeypatch.setattr(det, "QIM_DELTAS", (8, 16, 32))
    monkeypatch.setattr(det, "source_folds", lambda crops: iter([(crops[:-1], crops[-1:])]))
    expected_ref = np.concatenate([det.block_dct(c.image)[:, 3, 3] for c in train])
    original_peak = det._peak_score
    def checked_peak(image, reference):
        np.testing.assert_array_equal(reference, expected_ref)
        return original_peak(image, reference)
    monkeypatch.setattr(det, "_peak_score", checked_peak)
    original_ci = det.auc_with_ci
    monkeypatch.setattr(det, "auc_with_ci", lambda records: original_ci(records, n_boot=10))
    _, records, audits = det.evaluate_setting(train + test, 8, 2)
    _, _, changed = det.evaluate_setting(train + [crop("heldout", 99)], 8, 2)
    for key in ("train_sources", "cdf_boundary", "qim_delta", "dp_train_psnr", "qim_train_psnr"):
        assert audits[0][key] == changed[0][key]
    assert {r["source"] for r in records} == {"heldout"}
    assert audits[0]["test_sources"] == ["heldout"]
