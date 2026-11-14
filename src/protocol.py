"""Evaluation protocol v3: content-audited sources and explicit outer folds.

Fixes the v1 flaws found in review:
  * payload seeds come from crc32, not Python's per-process-salted hash();
  * real photos are cut into crops and every split is grouped by SOURCE
    photo, so no test crop shares a source with any training crop;
  * natural statistics (embedder CDFs and the attacker's reference) are
    fitted on training sources only;
  * confidence intervals come from a source-level bootstrap.
"""
from __future__ import annotations

import os
import hashlib
import importlib.metadata
import platform
import zlib
from dataclasses import dataclass

import numpy as np
from scipy.fftpack import dct

from .natural_cdf import BLOCK
from .utils import block_view, rgb_to_ycbcr

CROP = 256
PROTOCOL_VERSION = 3

# Real photographs bundled with scikit-image / matplotlib. Synthetic or
# non-photographic images (checkerboard, text, logos, phantoms) are excluded.
_SKIMAGE_SOURCES = [
    "astronaut", "chelsea", "coffee", "rocket",  # cat is an alias of chelsea
    "camera", "moon", "coins", "clock",                           # gray photos
    "brick", "grass", "gravel",                                   # gray textures
    "hubble_deep_field", "immunohistochemistry",                  # scientific photos
]


def stable_seed(name: str) -> int:
    """Process-independent seed (Python's hash() is salted per process)."""
    return zlib.crc32(name.encode("utf-8")) & 0x7FFFFFFF


def _to_rgb_uint8(arr: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr)
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    return arr[..., :3]


def image_hash(image: np.ndarray) -> str:
    a = np.ascontiguousarray(image)
    return hashlib.sha256(str((a.shape, a.dtype.str)).encode() + a.tobytes()).hexdigest()


def deduplicate_sources(sources):
    """Keep the lexicographically first name for each identical source image."""
    seen, unique, aliases = {}, {}, {}
    for name, image in sorted(sources.items()):
        digest = image_hash(image)
        if digest in seen:
            aliases[name] = seen[digest]
        else:
            seen[digest] = name
            unique[name] = image
    return unique, aliases


def validate_crops(crops):
    if not crops:
        raise ValueError("No crops available")
    names, hashes = set(), set()
    for crop in crops:
        digest = image_hash(crop.image)
        if crop.name in names or digest in hashes:
            raise ValueError("Duplicate crop identity or content: " + crop.name)
        names.add(crop.name)
        hashes.add(digest)


def assert_disjoint(train, test):
    if ({c.source for c in train} & {c.source for c in test}
            or {image_hash(c.image) for c in train} & {image_hash(c.image) for c in test}):
        raise ValueError("Source/content leakage across outer split")


def provenance(crops):
    validate_crops(crops)
    return {
        "protocol_version": PROTOCOL_VERSION,
        "python": platform.python_version(),
        "packages": {p: importlib.metadata.version(p) for p in
                     ("numpy", "scipy", "Pillow", "scikit-image", "scikit-learn", "matplotlib")},
        "known_excluded_aliases": {"cat": "chelsea"},
        "crop_count": len(crops), "source_count": len({c.source for c in crops}),
        "crops": [{"name": c.name, "source": c.source, "sha256": image_hash(c.image)} for c in crops],
        "folds": [{"train_sources": sorted({c.source for c in tr}),
                   "test_sources": sorted({c.source for c in te})} for tr, te in source_folds(crops)],
    }


def load_real_sources() -> dict[str, np.ndarray]:
    from skimage import data as skd
    out: dict[str, np.ndarray] = {}
    for name in _SKIMAGE_SOURCES:
        fn = getattr(skd, name)
        try:
            out[name] = _to_rgb_uint8(fn())
        except Exception as exc:
            raise RuntimeError("Required source unavailable: " + name) from exc
    try:
        import matplotlib
        from PIL import Image
        p = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data",
                         "sample_data", "grace_hopper.jpg")
        out["grace_hopper"] = np.asarray(Image.open(p).convert("RGB"), dtype=np.uint8)
    except Exception as exc:
        raise RuntimeError("Required source unavailable: grace_hopper") from exc
    return deduplicate_sources(out)[0]


@dataclass(frozen=True)
class Crop:
    source: str
    index: int
    image: np.ndarray

    @property
    def name(self) -> str:
        return f"{self.source}#{self.index}"


def real_crops(size: int = CROP, max_per_source: int = 4) -> list[Crop]:
    """Non-overlapping size x size crops, at most `max_per_source` per photo,
    taken on an evenly spaced grid so each source contributes varied content."""
    crops: list[Crop] = []
    for source, img in sorted(load_real_sources().items()):
        h, w = img.shape[:2]
        ny, nx = h // size, w // size
        cells = [(i, j) for i in range(ny) for j in range(nx)]
        if not cells:
            continue
        pick = np.linspace(0, len(cells) - 1, num=min(max_per_source, len(cells)))
        for k, c in enumerate(sorted({int(round(p)) for p in pick})):
            i, j = cells[c]
            crops.append(Crop(source, k, img[i * size:(i + 1) * size, j * size:(j + 1) * size]))
    validate_crops(crops)
    return crops


def source_folds(crops: list[Crop], k: int = 5, seed: int = 0):
    """Yield (train, test) crop lists with disjoint sources."""
    validate_crops(crops)
    sources = sorted({c.source for c in crops})
    if not 2 <= k <= len(sources):
        raise ValueError("Need at least k distinct sources and k >= 2")
    rng = np.random.default_rng(seed)
    order = [sources[i] for i in rng.permutation(len(sources))]
    groups = [order[i::k] for i in range(k)]
    for g in groups:
        test_src = set(g)
        train = [c for c in crops if c.source not in test_src]
        test = [c for c in crops if c.source in test_src]
        assert_disjoint(train, test)
        yield train, test


def _dct2(x):
    return dct(dct(x, axis=-1, norm="ortho"), axis=-2, norm="ortho")


def block_dct(img: np.ndarray) -> np.ndarray:
    """(n_blocks, 8, 8) luminance block-DCT of a block-aligned RGB image."""
    y = rgb_to_ycbcr(img)[..., 0]
    blocks = block_view(y, BLOCK).astype(np.float32)
    hb, wb = blocks.shape[:2]
    return _dct2(blocks).reshape(hb * wb, BLOCK, BLOCK)


def bootstrap_ci(per_unit: dict[str, list[float]], n_boot: int = 2000,
                 seed: int = 0, alpha: float = 0.05) -> tuple[float, float, float]:
    """Mean and (1-alpha) CI, resampling whole units (sources) with replacement."""
    keys = sorted(per_unit)
    vals = [np.asarray(per_unit[k], dtype=float) for k in keys]
    point = float(np.mean(np.concatenate(vals)))
    rng = np.random.default_rng(seed)
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, len(keys), size=len(keys))
        stats[b] = np.mean(np.concatenate([vals[i] for i in idx]))
    lo, hi = np.quantile(stats, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)
