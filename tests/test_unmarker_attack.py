import numpy as np
import pytest

from src.datasets import photo_synthetic
from src.dct_watermark import DCTWatermarkConfig
from src.dct_watermark import decode as dct_decode
from src.dct_watermark import encode as dct_encode
from src.metrics import bit_accuracy, psnr
from src.natural_cdf import collect_dct_coeffs, fit_natural_cdfs
from src.unmarker_attack import (
    UnMarkerConfig,
    attack,
    build_attacker_reference_from_cdfs,
    _flag_overdense_coeffs,
)
from src.utils import random_bits


@pytest.fixture(scope="module")
def nat_cdfs_and_ref():
    imgs = [photo_synthetic(i) for i in range(16)]
    coeffs = collect_dct_coeffs(imgs)
    cdfs = fit_natural_cdfs(coeffs, m=1, safety_margin=1.30)
    ref = build_attacker_reference_from_cdfs(cdfs)
    return cdfs, ref


def test_flag_overdense_fires_on_concentrated_mass(nat_cdfs_and_ref):
    _, ref = nat_cdfs_and_ref
    # Create coefficients mostly concentrated at one value (simulating QIM).
    rng = np.random.default_rng(0)
    coeffs = np.concatenate([
        np.full(200, 12.0, dtype=np.float32),   # fake QIM peak at +12
        rng.choice(ref[(3, 3)], size=800),
    ])
    mask = _flag_overdense_coeffs(coeffs, ref[(3, 3)], n_bins=64, ratio_threshold=2.0)
    # The 200 coefficients at value 12 should be flagged en masse.
    at_peak = (coeffs > 11) & (coeffs < 13)
    assert mask[at_peak].mean() > 0.8


def test_attack_preserves_shape_and_dtype(nat_cdfs_and_ref):
    _, ref = nat_cdfs_and_ref
    img = photo_synthetic(seed=42)
    cfg = UnMarkerConfig(attacker_reference=ref, peak_ratio_threshold=2.0)
    out = attack(img, cfg)
    assert out.shape == img.shape
    assert out.dtype == np.uint8


def test_attack_removes_qim_watermark(nat_cdfs_and_ref):
    """Peak-density attack should significantly reduce QIM bit accuracy."""
    _, ref = nat_cdfs_and_ref
    img = photo_synthetic(seed=100)
    cfg = DCTWatermarkConfig(delta=24, payload_bits=64, seed=1337)
    bits = random_bits(64, seed=1)
    wm = dct_encode(img, bits, cfg)
    id_acc = bit_accuracy(bits, dct_decode(wm, cfg))
    atk_cfg = UnMarkerConfig(attacker_reference=ref,
                              peak_ratio_threshold=2.0,
                              jitter_scale=1.0, seed=7)
    wm_atk = attack(wm, atk_cfg)
    atk_acc = bit_accuracy(bits, dct_decode(wm_atk, cfg))
    assert id_acc >= 0.99
    # Attack should hurt baseline notably.
    assert atk_acc < 0.85, f"attack only knocked QIM to {atk_acc}, expected <0.85"


def test_attack_preserves_perceptual_quality(nat_cdfs_and_ref):
    """Attack should leave the image visually usable (PSNR > 25 dB)."""
    _, ref = nat_cdfs_and_ref
    img = photo_synthetic(seed=55)
    cfg = UnMarkerConfig(attacker_reference=ref, peak_ratio_threshold=2.0,
                         jitter_scale=1.0)
    out = attack(img, cfg)
    assert psnr(img, out) > 25.0
