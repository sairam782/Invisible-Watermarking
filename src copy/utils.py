"""Image and payload utilities."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


def load_image_rgb(path: str | Path) -> np.ndarray:
    """Load an image as uint8 RGB HxWx3."""
    img = Image.open(path).convert("RGB")
    return np.asarray(img, dtype=np.uint8)


def save_image_rgb(arr: np.ndarray, path: str | Path) -> None:
    """Save a uint8 HxWx3 array as an image (format inferred from extension)."""
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(arr).save(path)


def rgb_to_ycbcr(rgb: np.ndarray) -> np.ndarray:
    """ITU-R BT.601 conversion. Input uint8, output float32 in [0, 255]."""
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = 128.0 - 0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 128.0 + 0.5 * r - 0.418688 * g - 0.081312 * b
    return np.stack([y, cb, cr], axis=-1)


def ycbcr_to_rgb(ycbcr: np.ndarray) -> np.ndarray:
    """Inverse of rgb_to_ycbcr. Input float32 in [0,255], output uint8 RGB."""
    y = ycbcr[..., 0]
    cb = ycbcr[..., 1] - 128.0
    cr = ycbcr[..., 2] - 128.0
    r = y + 1.402 * cr
    g = y - 0.344136 * cb - 0.714136 * cr
    b = y + 1.772 * cb
    rgb = np.stack([r, g, b], axis=-1)
    # np.astype(uint8) truncates; round first so quantization is symmetric
    # (asymmetric truncation biases DCT coefficients and breaks QIM decoding).
    return np.clip(np.round(rgb), 0, 255).astype(np.uint8)


def bits_from_bytes(data: bytes) -> np.ndarray:
    """Big-endian bit unpack: bytes -> uint8 array of {0,1}."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bytes_from_bits(bits: np.ndarray) -> bytes:
    """Inverse of bits_from_bytes. Length must be a multiple of 8."""
    bits = np.asarray(bits, dtype=np.uint8) & 1
    if bits.size % 8 != 0:
        pad = 8 - (bits.size % 8)
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    return np.packbits(bits).tobytes()


def random_bits(n: int, seed: int = 0) -> np.ndarray:
    """Deterministic random bit payload for benchmarking."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 2, size=n, dtype=np.uint8)


def payload_hash(bits: np.ndarray) -> str:
    """Short hex digest of a bit payload, for logging."""
    return hashlib.sha256(bytes_from_bits(bits)).hexdigest()[:12]


def block_view(arr: np.ndarray, block: int) -> np.ndarray:
    """Non-overlapping block view: (H,W) -> (H//b, W//b, b, b). Input must be block-divisible."""
    h, w = arr.shape
    if h % block or w % block:
        raise ValueError(f"array {arr.shape} not divisible by block size {block}")
    return arr.reshape(h // block, block, w // block, block).swapaxes(1, 2)


def unblock(blocks: np.ndarray) -> np.ndarray:
    """Inverse of block_view: (Hb, Wb, b, b) -> (Hb*b, Wb*b)."""
    hb, wb, b, _ = blocks.shape
    return blocks.swapaxes(1, 2).reshape(hb * b, wb * b)


def pad_to_multiple(arr: np.ndarray, block: int) -> tuple[np.ndarray, tuple[int, int]]:
    """Reflect-pad a 2D array so both dims are multiples of `block`. Returns (padded, original_shape)."""
    h, w = arr.shape
    ph = (-h) % block
    pw = (-w) % block
    if ph == 0 and pw == 0:
        return arr, (h, w)
    padded = np.pad(arr, ((0, ph), (0, pw)), mode="reflect")
    return padded, (h, w)


def crop_to(arr: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Undo pad_to_multiple by cropping to the given original shape."""
    h, w = shape
    return arr[:h, :w]
