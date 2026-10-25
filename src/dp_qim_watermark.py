"""Distribution-Preserving QIM (DP-QIM) invisible watermark.

Each payload bit snaps one mid-band DCT coefficient to a cell of a per-position
CDF-partitioned lattice whose label matches the bit. The 2M cells carry equal
natural mass, so the watermarked marginal matches the natural marginal — no
discrete peak structure for statistical attackers (UnMarker-class) to detect.

Target values are drawn from a per-cell `sample_pool` of natural samples
restricted to a safety-margin interior of the cell. This (a) preserves the
natural distribution (not a point-mass spike at a fixed value) and (b) keeps
written values far from cell boundaries so RGB→uint8 round-trip noise cannot
flip the decoded bit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

import numpy as np
from scipy.fftpack import dct, idct

from .natural_cdf import BLOCK, NaturalCDF
from .utils import (
    block_view,
    crop_to,
    pad_to_multiple,
    rgb_to_ycbcr,
    unblock,
    ycbcr_to_rgb,
)

DEFAULT_UV: tuple[int, int] = (3, 3)


def _dct2(x: np.ndarray) -> np.ndarray:
    return dct(dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _idct2(x: np.ndarray) -> np.ndarray:
    return idct(idct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


@dataclass(frozen=True)
class DPQIMConfig:
    seed: int = 1337
    payload_bits: int = 64
    uv: tuple[int, int] = DEFAULT_UV
    cdfs: Mapping[tuple[int, int], NaturalCDF] = field(default_factory=dict)

    def __post_init__(self):
        if self.uv not in self.cdfs:
            raise ValueError(
                f"no NaturalCDF supplied for uv={self.uv}. "
                f"Available: {sorted(self.cdfs.keys())[:5]}..."
            )


def _block_order(hb, wb, orig_shape, payload_bits, seed) -> np.ndarray:
    """Interior-only block indices (reflect-padded boundary blocks desync at decode)."""
    h, w = orig_shape
    vh, vw = h // BLOCK, w // BLOCK
    if vh == 0 or vw == 0:
        raise ValueError(f"image {orig_shape} smaller than one block")
    ii, jj = np.mgrid[0:vh, 0:vw]
    valid_flat = (ii * wb + jj).flatten()
    if payload_bits > valid_flat.size:
        raise ValueError(
            f"payload_bits={payload_bits} > capacity {valid_flat.size} "
            f"(interior blocks of a {h}x{w} image)."
        )
    rng = np.random.default_rng(seed)
    return valid_flat[rng.permutation(valid_flat.size)[:payload_bits]]


def _snap_to_correct_label(
    coeffs: np.ndarray,
    bits: np.ndarray,
    cdf: NaturalCDF,
    seed: int,
) -> np.ndarray:
    """Move each coefficient into an adjacent cell of correct label, sourcing
    the target value from that cell's natural sample pool.
    """
    labels = cdf.cell_labels()
    n_cells = labels.size
    pools = cdf.sample_pools
    if len(pools) != n_cells:
        raise ValueError(
            f"NaturalCDF has {len(pools)} pools but {n_cells} cells; "
            "was fit_natural_cdfs called with sample_pools disabled?"
        )

    cur_idx = cdf.cell_index(coeffs).astype(np.int64)
    cur_labels = labels[cur_idx]
    correct_mask = cur_labels == bits

    out = coeffs.copy().astype(np.float64)
    need_indices = np.where(~correct_mask)[0]
    if need_indices.size == 0:
        return out.astype(np.float32)

    rng = np.random.default_rng(seed)
    hashes = rng.integers(0, 2**31 - 1, size=coeffs.size)

    for i in need_indices:
        c = float(coeffs[i])
        k = int(cur_idx[i])
        candidates = []
        for k_target in (k - 1, k + 1):
            if 0 <= k_target < n_cells:
                pool = pools[k_target]
                pick = int(hashes[i]) % pool.size
                target = float(pool[pick])
                candidates.append((abs(c - target), target))
        _, chosen = min(candidates, key=lambda t: t[0])
        out[i] = chosen

    return out.astype(np.float32)


def encode(rgb: np.ndarray, bits: np.ndarray, cfg: DPQIMConfig) -> np.ndarray:
    bits = np.asarray(bits, dtype=np.uint8) & 1
    if bits.size != cfg.payload_bits:
        raise ValueError(f"expected {cfg.payload_bits} bits, got {bits.size}")

    ycc = rgb_to_ycbcr(rgb)
    y = ycc[..., 0]
    y_pad, orig_shape = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    n_blocks = hb * wb

    order = _block_order(hb, wb, orig_shape, cfg.payload_bits, cfg.seed)
    u, v = cfg.uv
    cdf = cfg.cdfs[cfg.uv]

    dct_blocks = _dct2(blocks)
    flat = dct_blocks.reshape(n_blocks, BLOCK, BLOCK)
    coeffs = flat[order, u, v]
    flat[order, u, v] = _snap_to_correct_label(coeffs, bits, cdf, cfg.seed)
    dct_blocks = flat.reshape(hb, wb, BLOCK, BLOCK)
    y_pad_wm = unblock(_idct2(dct_blocks))
    y_wm = crop_to(y_pad_wm, orig_shape)
    out = np.stack([y_wm, ycc[..., 1], ycc[..., 2]], axis=-1)
    return ycbcr_to_rgb(out)


def decode(rgb: np.ndarray, cfg: DPQIMConfig) -> np.ndarray:
    ycc = rgb_to_ycbcr(rgb)
    y = ycc[..., 0]
    orig_shape = y.shape
    y_pad, _ = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    n_blocks = hb * wb

    order = _block_order(hb, wb, orig_shape, cfg.payload_bits, cfg.seed)
    u, v = cfg.uv
    cdf = cfg.cdfs[cfg.uv]
    labels = cdf.cell_labels()

    dct_blocks = _dct2(blocks)
    flat = dct_blocks.reshape(n_blocks, BLOCK, BLOCK)
    coeffs = flat[order, u, v]
    idx = cdf.cell_index(coeffs)
    return labels[idx].astype(np.uint8)
