import numpy as np
import pytest

from src.dp_qim_watermark import DEFAULT_UV, DPQIMConfig, decode, encode
from src.metrics import bit_accuracy, psnr, ssim
from src.natural_cdf import collect_dct_coeffs, fit_natural_cdfs
from src.utils import random_bits


def _photo_like(seed: int, h: int = 256, w: int = 256) -> np.ndarray:
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = 128 + 40 * np.sin(xx / 30.0) + 30 * np.cos(yy / 25.0)
    texture = rng.laplace(0.0, 6.0, size=(h, w))
    y = np.clip(base + texture, 0, 255)
    rgb = np.stack([y, np.roll(y, 3, 0), np.roll(y, 3, 1)], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


@pytest.fixture(scope="module")
def natural_cdfs():
    imgs = [_photo_like(i) for i in range(16)]
    coeffs = collect_dct_coeffs(imgs)
    return fit_natural_cdfs(coeffs, m=1)


def test_roundtrip_recovers_all_bits(natural_cdfs):
    img = _photo_like(seed=42)
    cfg = DPQIMConfig(seed=1337, payload_bits=64, cdfs=natural_cdfs)
    bits = random_bits(cfg.payload_bits, seed=1)
    wm = encode(img, bits, cfg)
    recovered = decode(wm, cfg)
    assert bit_accuracy(bits, recovered) == 1.0


def test_missing_cdf_at_uv_raises(natural_cdfs):
    partial = {k: v for k, v in natural_cdfs.items() if k != DEFAULT_UV}
    with pytest.raises(ValueError):
        DPQIMConfig(payload_bits=64, cdfs=partial)


def test_watermark_stays_visually_close(natural_cdfs):
    img = _photo_like(seed=7)
    cfg = DPQIMConfig(payload_bits=64, cdfs=natural_cdfs)
    bits = random_bits(cfg.payload_bits, seed=2)
    wm = encode(img, bits, cfg)
    assert psnr(img, wm) > 38.0
    assert ssim(img, wm) > 0.98


def test_wrong_seed_gives_chance_accuracy(natural_cdfs):
    img = _photo_like(seed=3)
    enc_cfg = DPQIMConfig(seed=42, payload_bits=64, cdfs=natural_cdfs)
    dec_cfg = DPQIMConfig(seed=99, payload_bits=64, cdfs=natural_cdfs)
    bits = random_bits(enc_cfg.payload_bits, seed=3)
    wm = encode(img, bits, enc_cfg)
    acc = bit_accuracy(bits, decode(wm, dec_cfg))
    assert 0.35 < acc < 0.65


def test_free_lunch_half_bits_need_no_move(natural_cdfs):
    """Core DP-QIM claim: roughly half the coefficients already sit in a
    correct-label cell, so half the bits need zero perturbation."""
    from src.dp_qim_watermark import _snap_to_correct_label
    cdf = natural_cdfs[DEFAULT_UV]

    imgs = [_photo_like(i + 100) for i in range(4)]
    coeffs = collect_dct_coeffs(imgs)[:, DEFAULT_UV[0], DEFAULT_UV[1]]
    rng = np.random.default_rng(0)
    bits = rng.integers(0, 2, size=coeffs.size, dtype=np.uint8)
    new_coeffs = _snap_to_correct_label(coeffs, bits, cdf, seed=1337)
    unchanged_fraction = float(np.mean(new_coeffs == coeffs))
    assert 0.45 < unchanged_fraction < 0.55


def test_non_divisible_image_handled(natural_cdfs):
    img = _photo_like(seed=11, h=253, w=257)
    cfg = DPQIMConfig(payload_bits=32, cdfs=natural_cdfs)
    bits = random_bits(cfg.payload_bits, seed=4)
    wm = encode(img, bits, cfg)
    assert wm.shape == img.shape
    assert bit_accuracy(bits, decode(wm, cfg)) == 1.0
