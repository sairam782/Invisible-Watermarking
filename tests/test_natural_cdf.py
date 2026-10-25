import numpy as np
import pytest

from src.natural_cdf import (
    NaturalCDF,
    collect_dct_coeffs,
    fit_natural_cdfs,
    load_cdfs,
    save_cdfs,
)


def _photo_like(seed: int, h: int = 128, w: int = 128) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = 128 + 40 * np.sin(xx / 30.0) + 30 * np.cos(yy / 25.0)
    texture = rng.laplace(0.0, 5.0, size=(h, w))
    y = np.clip(base + texture, 0, 255)
    rgb = np.stack([y, np.roll(y, 3, 0), np.roll(y, 3, 1)], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def test_collect_dct_coeffs_shape():
    imgs = [_photo_like(i) for i in range(4)]
    coeffs = collect_dct_coeffs(imgs)
    assert coeffs.shape == (4 * 256, 8, 8)
    assert coeffs.dtype == np.float32


def test_collect_dct_rejects_non_rgb():
    with pytest.raises(ValueError):
        collect_dct_coeffs([np.zeros((32, 32), dtype=np.uint8)])


def test_fit_covers_all_non_dc_positions():
    imgs = [_photo_like(i) for i in range(6)]
    coeffs = collect_dct_coeffs(imgs)
    cdfs = fit_natural_cdfs(coeffs, m=4)
    assert len(cdfs) == 63
    assert (0, 0) not in cdfs


def test_fit_produces_equal_mass_cells():
    imgs = [_photo_like(i) for i in range(8)]
    coeffs = collect_dct_coeffs(imgs)
    m = 8
    cdfs = fit_natural_cdfs(coeffs, m=m)
    tolerance = 0.02
    for (u, v), cdf in cdfs.items():
        samples = coeffs[:, u, v]
        idx = cdf.cell_index(samples)
        assert idx.min() >= 0 and idx.max() < 2 * m
        counts = np.bincount(idx, minlength=2 * m)
        mass = counts / counts.sum()
        expected = 1.0 / (2 * m)
        assert np.all(np.abs(mass - expected) < tolerance)


def test_cell_labels_alternate():
    edges = np.array([-np.inf, -1.0, 0.0, 1.0, np.inf])
    centers = np.array([-2.0, -0.5, 0.5, 2.0])
    cdf = NaturalCDF(u=1, v=1, edges=edges, centers=centers, n_samples=100,
                     sample_pools=tuple(np.array([c], dtype=np.float32) for c in centers))
    assert np.array_equal(cdf.cell_labels(), np.array([0, 1, 0, 1], dtype=np.uint8))


def test_sample_pools_respect_safety_margin():
    imgs = [_photo_like(i) for i in range(8)]
    coeffs = collect_dct_coeffs(imgs)
    cdfs = fit_natural_cdfs(coeffs, m=2, safety_margin=2.0)
    for (u, v), cdf in cdfs.items():
        for i, pool in enumerate(cdf.sample_pools):
            lo, hi = cdf.edges[i], cdf.edges[i + 1]
            # every sample must be strictly inside the cell and at least
            # safety_margin from any FINITE boundary
            if np.isfinite(lo):
                assert np.all(pool >= lo + 2.0 - 1e-3) or pool.size <= 1
            if np.isfinite(hi):
                assert np.all(pool <= hi - 2.0 + 1e-3) or pool.size <= 1


def test_save_load_roundtrip(tmp_path):
    imgs = [_photo_like(i) for i in range(4)]
    coeffs = collect_dct_coeffs(imgs)
    cdfs = fit_natural_cdfs(coeffs, m=4)

    path = tmp_path / "cdfs.npz"
    save_cdfs(cdfs, path)
    loaded = load_cdfs(path)

    assert set(loaded.keys()) == set(cdfs.keys())
    for k in cdfs:
        np.testing.assert_array_equal(cdfs[k].edges, loaded[k].edges)
        np.testing.assert_allclose(cdfs[k].centers, loaded[k].centers, atol=1e-12)
        assert cdfs[k].n_samples == loaded[k].n_samples
        assert len(cdfs[k].sample_pools) == len(loaded[k].sample_pools)
