# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **real (9 images, 32614 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=2.5 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.1184**
- DCT-baseline (delta=64): **0.1680**
- DP-QIM: **0.1871**
- Ratio: DP-QIM is **0.90x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=64 | 57.20 | 0.9991 |
| DP-QIM | 58.11 | 0.9996 |
| Gap | 0.91 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 1.000 | +0.0 |
| jpeg_q90 | 1.000 | 0.863 | -13.7 ✗ |
| jpeg_q70 | 0.988 | 0.715 | -27.3 ✗ |
| jpeg_q40 | 0.474 | 0.606 | +13.2 ★ |
| jpeg_q20 | 0.476 | 0.547 | +7.1 ★ |
| gauss_noise_.01 | 0.986 | 0.915 | -7.1 ✗ |
| gauss_noise_.03 | 0.984 | 0.851 | -13.4 ✗ |
| gauss_blur_1.0 | 0.476 | 0.845 | +37.0 ★ |
| gauss_blur_2.0 | 0.476 | 0.595 | +12.0 ★ |
| resize_0.5 | 0.476 | 0.845 | +37.0 ★ |
| resize_2.0 | 0.977 | 0.965 | -1.2 |
| rot_5 | 0.965 | 0.938 | -2.8 |
| crop_0.9 | 0.939 | 0.953 | +1.4 |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 73.91 | 1.0000 | 0.1681 |
| 12 | 70.69 | 1.0000 | 0.1682 |
| 16 | 69.41 | 0.9999 | 0.1682 |
| 20 | 67.33 | 0.9999 | 0.1682 |
| 24 | 65.42 | 0.9999 | 0.1682 |
| 32 | 63.09 | 0.9997 | 0.1682 |
| 48 | 59.85 | 0.9995 | 0.1680 |
| 64 | 57.20 | 0.9991 | 0.1680 |
