import numpy as np
import pytest

from src.datasets import (
    crop_to_block_multiple,
    load_dataset,
    load_skimage_real,
    photo_synthetic,
    photo_synthetic_batch,
)


def test_load_skimage_real_returns_rgb_uint8():
    images = load_skimage_real(include_textures=False)
    assert len(images) >= 3, "should get at least astronaut/chelsea/coffee"
    for name, img in images:
        assert img.ndim == 3 and img.shape[-1] == 3, f"{name} not RGB"
        assert img.dtype == np.uint8, f"{name} not uint8"
        assert img.shape[0] >= 128 and img.shape[1] >= 128, f"{name} too small"


def test_textures_increase_count():
    photos = load_skimage_real(include_textures=False)
    with_tex = load_skimage_real(include_textures=True)
    assert len(with_tex) >= len(photos)


def test_synthetic_photo_shape_and_range():
    img = photo_synthetic(seed=42)
    assert img.shape == (256, 256, 3)
    assert img.dtype == np.uint8
    assert 10 < img.mean() < 245


def test_synthetic_batch_deterministic():
    a = photo_synthetic_batch(4, seed_offset=100)
    b = photo_synthetic_batch(4, seed_offset=100)
    for (na, ia), (nb, ib) in zip(a, b):
        assert na == nb
        np.testing.assert_array_equal(ia, ib)


def test_crop_to_block_multiple():
    img = np.zeros((253, 257, 3), dtype=np.uint8)
    out = crop_to_block_multiple(img, 8)
    assert out.shape[0] % 8 == 0 and out.shape[1] % 8 == 0
    assert out.shape[0] <= 253 and out.shape[1] <= 257
    assert out.shape[-1] == 3


def test_load_dataset_variants():
    assert len(load_dataset("real")) >= 3
    assert len(load_dataset("real_photos")) >= 3
    assert len(load_dataset("synth_8")) == 8
    assert len(load_dataset("synth_16")) == 16
    assert len(load_dataset("mixed_test")) >= 10


def test_unknown_dataset_raises():
    with pytest.raises(ValueError):
        load_dataset("not_a_dataset")


def test_missing_local_dir_returns_empty():
    # kodak/ may or may not exist in-repo — contract: empty list if missing.
    r = load_dataset("kodak")
    assert isinstance(r, list)
