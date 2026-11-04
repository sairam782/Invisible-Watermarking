"""Real + synthetic image dataset loader.

Primary source: scikit-image's bundled real photos (astronaut, chelsea,
coffee, cat, rocket) plus grayscale textures upcast to RGB (brick, grass,
gravel, camera). 9 real natural images total.

Secondary source: procedural photo-like synthetic images with Laplace
texture over a sinusoidal base. Used for (a) augmenting the CDF training
set, (b) fallback when external image downloads are unavailable.

Optional: if a local directory `data/<name>/` exists in the repo, we load
PNG/JPG files from it (so a user can drop Kodak-24 in `data/kodak/` and
`load_dataset('kodak')` picks it up).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = REPO_ROOT / "data"

# --- real scikit-image photos ---
_SKIMAGE_COLOR = [
    ("astronaut", "astronaut"),
    ("chelsea",   "chelsea"),
    ("coffee",    "coffee"),
    ("cat",       "cat"),
    ("rocket",    "rocket"),
]
_SKIMAGE_GRAY = [
    ("brick",  "brick"),
    ("grass",  "grass"),
    ("gravel", "gravel"),
    ("camera", "camera"),
]


def _to_rgb(arr: np.ndarray) -> np.ndarray:
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        return np.stack([arr, arr, arr], axis=-1)
    if arr.shape[-1] == 4:
        return arr[..., :3]
    return arr


def load_skimage_real(include_textures: bool = True) -> list[tuple[str, np.ndarray]]:
    """Return a list of (name, uint8 HxWx3) real images from scikit-image."""
    from skimage import data as skd
    out: list[tuple[str, np.ndarray]] = []
    for name, fn_name in _SKIMAGE_COLOR:
        try:
            arr = np.asarray(getattr(skd, fn_name)(), dtype=np.uint8)
            out.append((name, _to_rgb(arr)))
        except Exception:
            continue
    if include_textures:
        for name, fn_name in _SKIMAGE_GRAY:
            try:
                arr = np.asarray(getattr(skd, fn_name)(), dtype=np.uint8)
                out.append((name, _to_rgb(arr)))
            except Exception:
                continue
    return out


def load_from_dir(subdir: str, exts=(".png", ".jpg", ".jpeg", ".bmp")) -> list[tuple[str, np.ndarray]]:
    """Load all images from `data/<subdir>/`. Empty list if directory missing."""
    from PIL import Image
    d = DATA_ROOT / subdir
    if not d.exists():
        return []
    out = []
    for p in sorted(d.iterdir()):
        if p.suffix.lower() not in exts:
            continue
        try:
            arr = np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)
            out.append((p.stem, arr))
        except Exception:
            continue
    return out


def photo_synthetic(seed: int, h: int = 256, w: int = 256) -> np.ndarray:
    """Deterministic photo-like synthetic image.

    Sinusoidal low-frequency base + Laplace high-frequency texture — gives
    DCT coefficient statistics (heavy-tailed, roughly 1/f energy) that match
    natural-image prior work.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base = 128 + 40 * np.sin(xx / 30.0) + 30 * np.cos(yy / 25.0)
    texture = rng.laplace(0.0, 6.0, size=(h, w))
    y = np.clip(base + texture, 0, 255)
    rgb = np.stack([y, np.roll(y, 3, 0), np.roll(y, 3, 1)], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def photo_synthetic_batch(n: int, seed_offset: int = 0) -> list[tuple[str, np.ndarray]]:
    return [(f"synth_{i:03d}", photo_synthetic(seed_offset + i)) for i in range(n)]


def load_dataset(name: str) -> list[tuple[str, np.ndarray]]:
    """Load a named dataset.

    - "real": scikit-image real photos + textures (9 images).
    - "real_photos": just the 5 color photos (no textures).
    - "kodak": local `data/kodak/*.png` if present, else [].
    - "div2k_val": local `data/div2k_val/*.png` if present, else [].
    - "celeba_hq": local `data/celeba_hq/*.png` if present, else [].
    - "synth_16": 16 synthetic photo-like images for CDF training.
    - "synth_8":  8 synthetic photo-like images for CDF training.
    - "mixed_test": 9 real + 8 synthetic for a diverse test set.
    """
    if name == "real":
        return load_skimage_real(include_textures=True)
    if name == "real_photos":
        return load_skimage_real(include_textures=False)
    if name == "kodak":
        return load_from_dir("kodak")
    if name == "div2k_val":
        return load_from_dir("div2k_val")
    if name == "celeba_hq":
        return load_from_dir("celeba_hq")
    if name.startswith("synth_"):
        n = int(name.split("_", 1)[1])
        return photo_synthetic_batch(n, seed_offset=0)
    if name == "mixed_test":
        return load_skimage_real(True) + photo_synthetic_batch(8, seed_offset=1000)
    raise ValueError(f"unknown dataset {name!r}")


def crop_to_block_multiple(img: np.ndarray, block: int = 8) -> np.ndarray:
    """Crop so both dims are multiples of `block`."""
    h, w = img.shape[:2]
    return img[: (h // block) * block, : (w // block) * block]
