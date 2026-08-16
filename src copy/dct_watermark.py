"""Block-DCT invisible watermark using dither-modulation QIM.

Payload is embedded into the luminance channel of an RGB image. Each payload bit
is written into one 8x8 block's mid-frequency DCT coefficient via QIM. The
receiver knows the block order (via a shared seed) and the quantization step,
and recovers each bit by minimum-distance decoding.

This is a classical baseline. It is intentionally not the best-performing
scheme in the repo — it is the reference against which the hybrid method is
measured.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.fftpack import dct, idct

from .utils import (
    block_view,
    crop_to,
    pad_to_multiple,
    rgb_to_ycbcr,
    unblock,
    ycbcr_to_rgb,
)

BLOCK = 8
# Mid-frequency zigzag position; index (u, v) in the 8x8 DCT block.
# (4, 3) sits in the mid-band, robust to JPEG Q>=30 in practice.
MID_UV: tuple[int, int] = (4, 3)


def _dct2(block: np.ndarray) -> np.ndarray:
    return dct(dct(block, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _idct2(block: np.ndarray) -> np.ndarray:
    return idct(idct(block, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def _qim_embed(c: np.ndarray, bits: np.ndarray, delta: float) -> np.ndarray:
    """Dither-modulation QIM: snap coefficient to lattice L_b = {k*delta + b*delta/2}."""
    d = (bits.astype(np.float32) * 0.5) * delta
    return np.round((c - d) / delta) * delta + d


def _qim_decode(c: np.ndarray, delta: float) -> np.ndarray:
    """Minimum-distance decoder for the two-lattice QIM above."""
    # residue in [0, delta)
    r = np.mod(c, delta)
    # bit 0 if residue is near 0 or delta (i.e. near k*delta); bit 1 if near delta/2
    dist0 = np.minimum(r, delta - r)
    dist1 = np.abs(r - delta / 2.0)
    return (dist1 < dist0).astype(np.uint8)


@dataclass(frozen=True)
class DCTWatermarkConfig:
    delta: float = 16.0       # QIM step size (larger = more robust, less invisible)
    seed: int = 1337          # controls block selection order
    payload_bits: int = 64    # payload length in bits


def _block_order(num_blocks: int, payload_bits: int, seed: int) -> np.ndarray:
    if payload_bits > num_blocks:
        raise ValueError(
            f"payload_bits={payload_bits} exceeds available blocks={num_blocks}. "
            "Use a larger image or a shorter payload."
        )
    rng = np.random.default_rng(seed)
    return rng.permutation(num_blocks)[:payload_bits]


def encode(rgb: np.ndarray, bits: np.ndarray, cfg: DCTWatermarkConfig | None = None) -> np.ndarray:
    """Embed `bits` into `rgb` (HxWx3, uint8). Returns watermarked uint8 RGB."""
    cfg = cfg or DCTWatermarkConfig()
    bits = np.asarray(bits, dtype=np.uint8) & 1
    if bits.size != cfg.payload_bits:
        raise ValueError(f"expected {cfg.payload_bits} bits, got {bits.size}")

    ycc = rgb_to_ycbcr(rgb)
    y = ycc[..., 0]
    y_pad, orig_shape = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)   # (Hb, Wb, 8, 8)
    hb, wb, _, _ = blocks.shape
    n_blocks = hb * wb

    order = _block_order(n_blocks, cfg.payload_bits, cfg.seed)
    u, v = MID_UV

    dct_blocks = _dct2(blocks)                              # (Hb, Wb, 8, 8)
    flat = dct_blocks.reshape(n_blocks, BLOCK, BLOCK)
    coeffs = flat[order, u, v]
    flat[order, u, v] = _qim_embed(coeffs, bits, cfg.delta)
    dct_blocks = flat.reshape(hb, wb, BLOCK, BLOCK)

    y_pad_wm = unblock(_idct2(dct_blocks))
    y_wm = crop_to(y_pad_wm, orig_shape)

    out = np.stack([y_wm, ycc[..., 1], ycc[..., 2]], axis=-1)
    return ycbcr_to_rgb(out)


def decode(rgb: np.ndarray, cfg: DCTWatermarkConfig | None = None) -> np.ndarray:
    """Recover `payload_bits` bits from a (possibly attacked) watermarked image."""
    cfg = cfg or DCTWatermarkConfig()
    ycc = rgb_to_ycbcr(rgb)
    y = ycc[..., 0]
    y_pad, _ = pad_to_multiple(y, BLOCK)
    blocks = block_view(y_pad, BLOCK).astype(np.float32)
    hb, wb, _, _ = blocks.shape
    n_blocks = hb * wb

    order = _block_order(n_blocks, cfg.payload_bits, cfg.seed)
    u, v = MID_UV

    dct_blocks = _dct2(blocks)
    flat = dct_blocks.reshape(n_blocks, BLOCK, BLOCK)
    coeffs = flat[order, u, v]
    return _qim_decode(coeffs, cfg.delta)
