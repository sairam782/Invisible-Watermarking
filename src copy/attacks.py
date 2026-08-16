"""Image attacks used to stress-test watermark robustness.

Every attack takes a uint8 RGB HxWx3 array and returns a uint8 RGB array of the
same shape (attacks that change the geometry pad/crop back to the original).
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Callable

import numpy as np
from PIL import Image, ImageFilter


Attack = Callable[[np.ndarray], np.ndarray]


def jpeg(quality: int) -> Attack:
    def _apply(rgb: np.ndarray) -> np.ndarray:
        buf = io.BytesIO()
        Image.fromarray(rgb).save(buf, format="JPEG", quality=int(quality))
        buf.seek(0)
        return np.asarray(Image.open(buf).convert("RGB"), dtype=np.uint8)
    _apply.__name__ = f"jpeg_q{quality}"
    return _apply


def gaussian_noise(sigma: float) -> Attack:
    """Additive Gaussian noise; sigma is in units of 1.0 = full dynamic range."""
    def _apply(rgb: np.ndarray) -> np.ndarray:
        rng = np.random.default_rng(0)
        noise = rng.normal(0.0, sigma * 255.0, size=rgb.shape)
        out = rgb.astype(np.float32) + noise
        return np.clip(out, 0, 255).astype(np.uint8)
    _apply.__name__ = f"gauss_noise_s{sigma}"
    return _apply


def gaussian_blur(radius: float) -> Attack:
    def _apply(rgb: np.ndarray) -> np.ndarray:
        img = Image.fromarray(rgb).filter(ImageFilter.GaussianBlur(radius=radius))
        return np.asarray(img, dtype=np.uint8)
    _apply.__name__ = f"gauss_blur_r{radius}"
    return _apply


def center_crop_pad(keep_fraction: float) -> Attack:
    """Center-crop keeping `keep_fraction` of area, then pad back with zeros.

    A decoder that reads block positions modulo image size will lose sync under
    this attack; that is exactly what we want to measure.
    """
    def _apply(rgb: np.ndarray) -> np.ndarray:
        h, w = rgb.shape[:2]
        side = keep_fraction ** 0.5
        ch, cw = int(round(h * side)), int(round(w * side))
        y0 = (h - ch) // 2
        x0 = (w - cw) // 2
        cropped = rgb[y0:y0 + ch, x0:x0 + cw]
        out = np.zeros_like(rgb)
        out[y0:y0 + ch, x0:x0 + cw] = cropped
        return out
    _apply.__name__ = f"crop_pad_{keep_fraction}"
    return _apply


def resize_roundtrip(scale: float) -> Attack:
    """Downscale-then-upscale (or up-then-down) back to original shape."""
    def _apply(rgb: np.ndarray) -> np.ndarray:
        h, w = rgb.shape[:2]
        nh, nw = max(1, int(round(h * scale))), max(1, int(round(w * scale)))
        img = Image.fromarray(rgb).resize((nw, nh), Image.BICUBIC)
        img = img.resize((w, h), Image.BICUBIC)
        return np.asarray(img, dtype=np.uint8)
    _apply.__name__ = f"resize_rt_{scale}"
    return _apply


def rotation(degrees: float) -> Attack:
    """Rotate then rotate back (loses information near borders)."""
    def _apply(rgb: np.ndarray) -> np.ndarray:
        img = Image.fromarray(rgb).rotate(degrees, resample=Image.BICUBIC)
        img = img.rotate(-degrees, resample=Image.BICUBIC)
        return np.asarray(img, dtype=np.uint8)
    _apply.__name__ = f"rot_{degrees}"
    return _apply


def identity() -> Attack:
    def _apply(rgb: np.ndarray) -> np.ndarray:
        return rgb
    _apply.__name__ = "identity"
    return _apply


@dataclass(frozen=True)
class AttackSuite:
    """Ordered set of named attacks for a benchmark row."""
    attacks: tuple[tuple[str, Attack], ...]

    @staticmethod
    def default() -> "AttackSuite":
        return AttackSuite((
            ("identity",       identity()),
            ("jpeg_q90",       jpeg(90)),
            ("jpeg_q70",       jpeg(70)),
            ("jpeg_q40",       jpeg(40)),
            ("jpeg_q20",       jpeg(20)),
            ("gauss_noise_.01", gaussian_noise(0.01)),
            ("gauss_noise_.03", gaussian_noise(0.03)),
            ("gauss_blur_1.0", gaussian_blur(1.0)),
            ("gauss_blur_2.0", gaussian_blur(2.0)),
            ("resize_0.5",     resize_roundtrip(0.5)),
            ("resize_2.0",     resize_roundtrip(2.0)),
            ("rot_5",          rotation(5)),
            ("crop_0.9",       center_crop_pad(0.9)),
        ))
