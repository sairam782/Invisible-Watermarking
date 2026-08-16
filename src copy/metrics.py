"""Fidelity + robustness metrics used across experiments."""
from __future__ import annotations

import numpy as np
from skimage.metrics import structural_similarity as _ssim


def psnr(cover: np.ndarray, stego: np.ndarray, data_range: float = 255.0) -> float:
    """Peak signal-to-noise ratio between two uint8 (or float) images."""
    cover = cover.astype(np.float64)
    stego = stego.astype(np.float64)
    mse = float(np.mean((cover - stego) ** 2))
    if mse == 0.0:
        return float("inf")
    return 10.0 * np.log10((data_range ** 2) / mse)


def ssim(cover: np.ndarray, stego: np.ndarray) -> float:
    """Mean SSIM across channels; works for RGB or grayscale."""
    if cover.ndim == 3:
        return float(_ssim(cover, stego, channel_axis=-1, data_range=255))
    return float(_ssim(cover, stego, data_range=255))


def bit_accuracy(true_bits: np.ndarray, recovered_bits: np.ndarray) -> float:
    """Fraction of correctly recovered bits."""
    a = np.asarray(true_bits, dtype=np.uint8) & 1
    b = np.asarray(recovered_bits, dtype=np.uint8) & 1
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    return float(np.mean(a == b))


def bit_error_rate(true_bits: np.ndarray, recovered_bits: np.ndarray) -> float:
    return 1.0 - bit_accuracy(true_bits, recovered_bits)
