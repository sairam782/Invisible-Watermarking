"""Empirical per-position DCT coefficient CDFs for Distribution-Preserving QIM.

For each of the 63 non-DC positions (u, v) in the 8x8 block-DCT, we fit the
empirical distribution of coefficient values across a training set of natural
images, store it as 2M equal-mass cells with alternating labels {0,1,0,1,...},
and keep a per-cell `sample_pool` — natural samples lying inside the cell AND
at least `safety_margin` away from either boundary. DP-QIM uses these pools
as target values at encode time, so the watermarked marginal distribution
follows the natural distribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.fftpack import dct

from .utils import block_view, pad_to_multiple, rgb_to_ycbcr

BLOCK = 8


def _dct2(x: np.ndarray) -> np.ndarray:
    return dct(dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def collect_dct_coeffs(images: Iterable[np.ndarray]) -> np.ndarray:
    """Stack per-block DCT coefficients from a set of uint8 RGB images.

    Returns (n_blocks_total, 8, 8) float32 — DCT of every 8x8 luminance block.
    """
    per_image_blocks: list[np.ndarray] = []
    for img in images:
        if img.ndim != 3 or img.shape[-1] != 3:
            raise ValueError(f"expected HxWx3 RGB image, got shape {img.shape}")
        y = rgb_to_ycbcr(img)[..., 0]
        y_pad, _ = pad_to_multiple(y, BLOCK)
        blocks = block_view(y_pad, BLOCK).astype(np.float32)
        hb, wb, _, _ = blocks.shape
        per_image_blocks.append(_dct2(blocks).reshape(hb * wb, BLOCK, BLOCK))
    if not per_image_blocks:
        raise ValueError("no images provided")
    return np.concatenate(per_image_blocks, axis=0)


@dataclass(frozen=True)
class NaturalCDF:
    """Empirical CDF for one (u, v) position, with CDF-partitioned cells.

    `sample_pools[i]` is an array of up to `max_pool_size` natural samples
    inside cell i AND at least `safety_margin` away from either edge. DP-QIM
    reads from these pools so the watermark's marginal matches natural.
    """
    u: int
    v: int
    edges: np.ndarray            # (2M+1,) sorted; edges[0]=-inf, edges[-1]=+inf
    centers: np.ndarray          # (2M,) median of samples per cell
    n_samples: int
    sample_pools: tuple[np.ndarray, ...] = ()

    @property
    def m(self) -> int:
        return (self.edges.size - 1) // 2

    def cell_labels(self) -> np.ndarray:
        return np.arange(2 * self.m, dtype=np.uint8) & 1

    def cell_index(self, coeffs: np.ndarray) -> np.ndarray:
        interior = self.edges[1:-1]
        return np.searchsorted(interior, coeffs, side="right").astype(np.int64)


def fit_natural_cdfs(
    dct_coeffs: np.ndarray,
    m: int,
    safety_margin: float = 3.0,
    max_pool_size: int = 512,
    rng_seed: int = 0,
) -> dict[tuple[int, int], NaturalCDF]:
    """Fit a NaturalCDF with 2M cells for every non-DC position."""
    if m < 1:
        raise ValueError("m must be >= 1")
    n_blocks = dct_coeffs.shape[0]
    if n_blocks < 2 * m:
        raise ValueError(f"need at least 2M={2*m} samples per position, got {n_blocks}")

    rng = np.random.default_rng(rng_seed)
    out: dict[tuple[int, int], NaturalCDF] = {}
    percentiles = np.linspace(0.0, 100.0, 2 * m + 1)
    for u in range(BLOCK):
        for v in range(BLOCK):
            if u == 0 and v == 0:
                continue
            samples = dct_coeffs[:, u, v]
            interior_edges = np.percentile(samples, percentiles[1:-1])
            interior_edges = _make_strictly_increasing(interior_edges)
            edges = np.concatenate([[-np.inf], interior_edges, [np.inf]])
            centers = _cell_centers(samples, edges)
            pools = _cell_sample_pools(samples, edges, safety_margin, max_pool_size, rng)
            out[(u, v)] = NaturalCDF(
                u=u, v=v, edges=edges, centers=centers, n_samples=n_blocks,
                sample_pools=tuple(pools),
            )
    return out


def _make_strictly_increasing(x: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    x = x.astype(np.float64).copy()
    for i in range(1, x.size):
        if x[i] <= x[i - 1]:
            x[i] = x[i - 1] + eps
    return x


def _cell_centers(samples: np.ndarray, edges: np.ndarray) -> np.ndarray:
    n_cells = edges.size - 1
    centers = np.empty(n_cells, dtype=np.float64)
    for i in range(n_cells):
        lo, hi = edges[i], edges[i + 1]
        mask = (samples > lo) & (samples <= hi)
        if mask.any():
            centers[i] = np.median(samples[mask])
        else:
            if np.isfinite(lo) and np.isfinite(hi):
                centers[i] = 0.5 * (lo + hi)
            elif np.isfinite(hi):
                centers[i] = hi - 1.0
            elif np.isfinite(lo):
                centers[i] = lo + 1.0
            else:
                centers[i] = 0.0
    return centers


def _cell_sample_pools(samples, edges, safety_margin, max_pool_size, rng) -> list[np.ndarray]:
    pools: list[np.ndarray] = []
    n_cells = edges.size - 1
    for i in range(n_cells):
        lo, hi = edges[i], edges[i + 1]
        lo_safe = lo + safety_margin if np.isfinite(lo) else -np.inf
        hi_safe = hi - safety_margin if np.isfinite(hi) else np.inf
        if lo_safe >= hi_safe:
            mask = (samples > lo) & (samples <= hi)
            if mask.any():
                pools.append(np.array([float(np.median(samples[mask]))], dtype=np.float32))
            else:
                pools.append(np.array([0.5 * (max(lo, -100.0) + min(hi, 100.0))], dtype=np.float32))
            continue
        mask = (samples > lo_safe) & (samples <= hi_safe)
        cell_samples = samples[mask]
        if cell_samples.size == 0:
            lo_f = lo_safe if np.isfinite(lo_safe) else hi_safe - 2 * safety_margin
            hi_f = hi_safe if np.isfinite(hi_safe) else lo_safe + 2 * safety_margin
            pools.append(np.array([0.5 * (lo_f + hi_f)], dtype=np.float32))
            continue
        if cell_samples.size > max_pool_size:
            idx = rng.choice(cell_samples.size, size=max_pool_size, replace=False)
            cell_samples = cell_samples[idx]
        pools.append(cell_samples.astype(np.float32))
    return pools


def save_cdfs(cdfs: dict[tuple[int, int], NaturalCDF], path: str | Path) -> None:
    keys = sorted(cdfs.keys())
    packed: dict[str, np.ndarray] = {}
    for (u, v) in keys:
        c = cdfs[(u, v)]
        packed[f"edges_{u}_{v}"] = c.edges
        packed[f"centers_{u}_{v}"] = c.centers
        for i, pool in enumerate(c.sample_pools):
            packed[f"pool_{u}_{v}_{i}"] = pool
        packed[f"pool_sizes_{u}_{v}"] = np.array(
            [len(p) for p in c.sample_pools], dtype=np.int64
        )
    packed["_positions"] = np.array(keys, dtype=np.int32)
    packed["_n_samples"] = np.array([next(iter(cdfs.values())).n_samples], dtype=np.int64)
    np.savez(path, **packed)


def load_cdfs(path: str | Path) -> dict[tuple[int, int], NaturalCDF]:
    data = np.load(path, allow_pickle=False)
    positions = data["_positions"]
    n_samples = int(data["_n_samples"][0])
    out: dict[tuple[int, int], NaturalCDF] = {}
    for uv in positions:
        u, v = int(uv[0]), int(uv[1])
        edges = data[f"edges_{u}_{v}"]
        centers = data[f"centers_{u}_{v}"]
        pool_sizes_key = f"pool_sizes_{u}_{v}"
        pools: tuple[np.ndarray, ...] = ()
        if pool_sizes_key in data.files:
            n_cells = len(data[pool_sizes_key])
            pools = tuple(data[f"pool_{u}_{v}_{i}"] for i in range(n_cells))
        out[(u, v)] = NaturalCDF(
            u=u, v=v, edges=edges, centers=centers, n_samples=n_samples,
            sample_pools=pools,
        )
    return out
