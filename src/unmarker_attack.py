"""UnMarker-style statistical-anomaly attack.

A faithful-in-spirit reimplementation of the UnMarker attack
(Barzegar & AlBadawy, IEEE S&P 2025). The original is fully black-box;
ours follows the same mechanism.

**Key insight (per the paper + press coverage):** classical QIM watermarks
create *peak-density artifacts* in the marginal of a DCT coefficient ---
many blocks cluster at the same lattice points. The natural distribution
is smooth, so an attacker can detect these peaks via histogram
over-concentration relative to a natural reference, then disperse them
by adding targeted noise to the clustered coefficients.

Our attack:

  1. For each (u,v) position, build the per-block histogram of the
     received image's DCT coefficient values and compare against the
     natural-reference histogram (both on a common bin edge set).
  2. Identify bins where the received histogram is significantly
     over-concentrated relative to natural (overdensity ratio >
     `peak_ratio_threshold`).
  3. For blocks whose coefficient falls into an over-dense bin, add
     Gaussian jitter of standard deviation proportional to the local
     natural spread at that coefficient value. Jitter spreads the
     peak back toward natural density.
  4. IDCT; return the de-watermarked image.

Preserves perceptual quality: only blocks implicated in a peak get
jittered, and the jitter is calibrated to the local natural scale.
No queries to the watermark decoder; no knowledge of the key.
"""
from __future__ import annotations

from dataclasses import dataclass
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


def _dct2(x):
    return dct(dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _idct2(x):
    return idct(idct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


@dataclass(frozen=True)
class UnMarkerConfig:
    """Attack hyperparameters.

    peak_ratio_threshold: a bin is 'over-dense' when its mass in the
      received histogram divided by its mass in the natural reference
      exceeds this ratio. 2.0 = moved only if twice as dense as natural.
    n_bins: number of bins per (u,v) position for the detection
      histogram. Too few = can't localize peaks, too many = noisy
      per-bin counts. 64 is a reasonable compromise.
    jitter_scale: Gaussian noise std added to flagged coefficients,
      in units of the local natural inter-quartile range. 0.5 =
      jitter of half the natural scale (significant but not destructive).
    attacker_reference: per-(u,v) natural-coefficient reference samples.
    uv_subset: restrict the attack. Default: all non-DC positions.
    seed: for deterministic jitter.
    """
    peak_ratio_threshold: float = 2.0
    n_bins: int = 64
    jitter_scale: float = 0.5
    attacker_reference: Mapping[tuple[int, int], np.ndarray] = None   # type: ignore[assignment]
    uv_subset: tuple[tuple[int, int], ...] | None = None
    seed: int = 7


def _flag_overdense_coeffs(
    coeffs: np.ndarray,
    reference: np.ndarray,
    n_bins: int,
    ratio_threshold: float,
) -> np.ndarray:
    """Return a boolean mask marking coefficients in over-dense bins."""
    lo = min(float(np.min(coeffs)), float(np.min(reference)))
    hi = max(float(np.max(coeffs)), float(np.max(reference)))
    if lo >= hi:
        return np.zeros_like(coeffs, dtype=bool)
    edges = np.linspace(lo, hi, n_bins + 1)
    hist_rx, _ = np.histogram(coeffs, bins=edges, density=False)
    hist_ref, _ = np.histogram(reference, bins=edges, density=False)

    # Mass-normalize
    p_rx = hist_rx / max(coeffs.size, 1)
    p_ref = hist_ref / max(reference.size, 1)
    # Smooth the reference slightly so we don't divide by zero in empty bins.
    p_ref_smooth = np.maximum(p_ref, 1.0 / (2 * reference.size)) if reference.size else p_ref
    ratio = p_rx / p_ref_smooth
    bad_bins = ratio > ratio_threshold

    # Which coefficients fall into bad bins?
    coeff_bin = np.clip(np.searchsorted(edges[1:-1], coeffs), 0, n_bins - 1)
    return bad_bins[coeff_bin]


def _jitter(coeffs: np.ndarray, reference: np.ndarray,
            mask: np.ndarray, jitter_scale: float,
            rng: np.random.Generator) -> np.ndarray:
    """Add scaled Gaussian jitter to flagged coefficients."""
    if not mask.any() or reference.size == 0:
        return coeffs.astype(np.float32)
    # Natural IQR as a robust spread estimate.
    q1, q3 = np.percentile(reference, [25, 75])
    sigma = jitter_scale * (q3 - q1)
    out = coeffs.astype(np.float64).copy()
    noise = rng.normal(0.0, sigma, size=int(mask.sum()))
    out[mask] = out[mask] + noise
    return out.astype(np.float32)


def attack(rgb: np.ndarray, cfg: UnMarkerConfig) -> np.ndarray:
    """Apply the UnMarker-style peak-density attack. Returns uint8 RGB."""
    if cfg.attacker_reference is None:
        raise ValueError("UnMarkerConfig.attacker_reference must be set")

    ycc = rgb_to_ycbcr(rgb)
    y = ycc[..., 0]
    orig_shape = y.shape
    y_pad, _ = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    n_blocks = hb * wb

    dct_blocks = _dct2(blocks)
    flat = dct_blocks.reshape(n_blocks, BLOCK, BLOCK)

    rng = np.random.default_rng(cfg.seed)
    positions = cfg.uv_subset or tuple(
        (u, v) for u in range(BLOCK) for v in range(BLOCK) if (u, v) != (0, 0)
    )

    for (u, v) in positions:
        ref = cfg.attacker_reference.get((u, v))
        if ref is None or ref.size < 32:
            continue
        coeffs = flat[:, u, v]
        bad_mask = _flag_overdense_coeffs(
            coeffs, ref, cfg.n_bins, cfg.peak_ratio_threshold
        )
        if not bad_mask.any():
            continue
        flat[:, u, v] = _jitter(coeffs, ref, bad_mask, cfg.jitter_scale, rng)

    dct_blocks = flat.reshape(hb, wb, BLOCK, BLOCK)
    y_pad_wm = unblock(_idct2(dct_blocks))
    y_wm = crop_to(y_pad_wm, orig_shape)
    out_ycc = np.stack([y_wm, ycc[..., 1], ycc[..., 2]], axis=-1)
    return ycbcr_to_rgb(out_ycc)


def make_attack(cfg: UnMarkerConfig):
    """Return an attack callable matching the AttackSuite convention."""
    def _apply(rgb: np.ndarray) -> np.ndarray:
        return attack(rgb, cfg)
    _apply.__name__ = (f"unmarker_r{cfg.peak_ratio_threshold}"
                        f"_j{cfg.jitter_scale}")
    return _apply


def build_attacker_reference_from_cdfs(
    cdfs: dict[tuple[int, int], NaturalCDF],
) -> dict[tuple[int, int], np.ndarray]:
    """Flatten per-cell sample pools into a reference bank per uv."""
    out = {}
    for uv, cdf in cdfs.items():
        samples = np.concatenate([p for p in cdf.sample_pools if p.size > 0])
        out[uv] = samples.astype(np.float32)
    return out
