import numpy as np

from src.attacks import (
    AttackSuite,
    center_crop_pad,
    gaussian_blur,
    gaussian_noise,
    identity,
    jpeg,
    resize_roundtrip,
    rotation,
)
from src.metrics import bit_accuracy, bit_error_rate, psnr, ssim


def _img(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=(128, 128, 3), dtype=np.uint8)


def test_psnr_identical_is_inf():
    img = _img()
    assert psnr(img, img) == float("inf")


def test_psnr_and_ssim_monotone_under_noise():
    img = _img()
    low = gaussian_noise(0.01)(img)
    high = gaussian_noise(0.1)(img)
    assert psnr(img, low) > psnr(img, high)
    assert ssim(img, low) > ssim(img, high)


def test_bit_accuracy_and_ber_are_complements():
    a = np.array([0, 1, 0, 1, 1, 0, 0, 1], dtype=np.uint8)
    b = np.array([0, 1, 1, 1, 0, 0, 0, 1], dtype=np.uint8)
    assert abs(bit_accuracy(a, b) + bit_error_rate(a, b) - 1.0) < 1e-9


def test_attacks_preserve_shape_and_dtype():
    img = _img()
    attacks = [
        identity(),
        jpeg(70),
        gaussian_noise(0.02),
        gaussian_blur(1.5),
        center_crop_pad(0.8),
        resize_roundtrip(0.5),
        rotation(5),
    ]
    for a in attacks:
        out = a(img)
        assert out.shape == img.shape, f"{a.__name__} changed shape"
        assert out.dtype == np.uint8, f"{a.__name__} changed dtype"


def test_default_attack_suite_runs():
    suite = AttackSuite.default()
    img = _img()
    for name, atk in suite.attacks:
        out = atk(img)
        assert out.shape == img.shape, f"{name} broke shape"
