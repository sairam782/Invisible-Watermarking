import numpy as np
import pytest

from src.dct_watermark import DCTWatermarkConfig, decode, encode
from src.metrics import bit_accuracy, psnr, ssim
from src.utils import random_bits


def _synthetic_image(h: int = 256, w: int = 256, seed: int = 0) -> np.ndarray:
    """Deterministic natural-ish test image: low-frequency gradient + high-frequency texture."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = 128 + 60 * np.sin(xx / 40.0) + 40 * np.cos(yy / 30.0)
    texture = rng.normal(0, 12, size=(h, w))
    y = np.clip(base + texture, 0, 255)
    rgb = np.stack([y, np.roll(y, 5, axis=0), np.roll(y, 5, axis=1)], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def test_roundtrip_recovers_all_bits_no_attack():
    img = _synthetic_image()
    cfg = DCTWatermarkConfig(delta=16.0, seed=42, payload_bits=64)
    bits = random_bits(cfg.payload_bits, seed=1)

    wm = encode(img, bits, cfg)
    recovered = decode(wm, cfg)

    assert bit_accuracy(bits, recovered) == 1.0


def test_watermark_is_visually_close_to_cover():
    img = _synthetic_image()
    cfg = DCTWatermarkConfig(delta=16.0, seed=42, payload_bits=64)
    bits = random_bits(cfg.payload_bits, seed=2)

    wm = encode(img, bits, cfg)

    assert psnr(img, wm) > 40.0, "watermark should be near-invisible at delta=16"
    assert ssim(img, wm) > 0.99


def test_different_payloads_yield_different_stego():
    img = _synthetic_image()
    cfg = DCTWatermarkConfig(delta=16.0, seed=42, payload_bits=64)
    bits_a = random_bits(cfg.payload_bits, seed=1)
    bits_b = random_bits(cfg.payload_bits, seed=2)

    wm_a = encode(img, bits_a, cfg)
    wm_b = encode(img, bits_b, cfg)

    assert not np.array_equal(wm_a, wm_b)


def test_wrong_seed_cannot_recover_bits():
    img = _synthetic_image()
    cfg_enc = DCTWatermarkConfig(delta=16.0, seed=42, payload_bits=64)
    cfg_dec = DCTWatermarkConfig(delta=16.0, seed=99, payload_bits=64)
    bits = random_bits(cfg_enc.payload_bits, seed=3)

    wm = encode(img, bits, cfg_enc)
    recovered = decode(wm, cfg_dec)

    acc = bit_accuracy(bits, recovered)
    # With wrong seed the decoder reads unrelated blocks — accuracy should be near chance.
    assert 0.35 < acc < 0.65


def test_payload_larger_than_capacity_raises():
    img = _synthetic_image(64, 64)   # 8x8 blocks: 64 blocks total
    cfg = DCTWatermarkConfig(delta=16.0, seed=1, payload_bits=65)
    bits = random_bits(cfg.payload_bits, seed=1)
    with pytest.raises(ValueError):
        encode(img, bits, cfg)


def test_non_divisible_image_is_handled():
    img = _synthetic_image(h=253, w=257)   # not a multiple of 8
    cfg = DCTWatermarkConfig(delta=16.0, seed=42, payload_bits=32)
    bits = random_bits(cfg.payload_bits, seed=4)

    wm = encode(img, bits, cfg)
    recovered = decode(wm, cfg)

    assert wm.shape == img.shape
    assert bit_accuracy(bits, recovered) == 1.0
