# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **real (9 images, 32614 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=4.0 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.1184**
- DCT-baseline (delta=64): **0.1680**
- DP-QIM: **0.2130**
- Ratio: DP-QIM is **0.79x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=64 | 57.28 | 0.9991 |
| DP-QIM | 56.58 | 0.9994 |
| Gap | 0.70 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 1.000 | +0.0 |
| jpeg_q90 | 1.000 | 0.868 | -13.2 ✗ |
| jpeg_q70 | 0.993 | 0.714 | -28.0 ✗ |
| jpeg_q40 | 0.498 | 0.648 | +14.9 ★ |
| jpeg_q20 | 0.500 | 0.526 | +2.6 |
| gauss_noise_.01 | 0.993 | 0.917 | -7.6 ✗ |
| gauss_noise_.03 | 0.990 | 0.866 | -12.3 ✗ |
| gauss_blur_1.0 | 0.498 | 0.877 | +37.8 ★ |
| gauss_blur_2.0 | 0.500 | 0.620 | +12.0 ★ |
| resize_0.5 | 0.500 | 0.830 | +33.0 ★ |
| resize_2.0 | 0.986 | 0.958 | -2.8 |
| rot_5 | 0.976 | 0.948 | -2.8 |
| crop_0.9 | 0.946 | 0.939 | -0.7 |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 74.01 | 1.0000 | 0.1682 |
| 12 | 70.71 | 1.0000 | 0.1682 |
| 16 | 69.61 | 1.0000 | 0.1682 |
| 20 | 67.54 | 0.9999 | 0.1682 |
| 24 | 65.72 | 0.9999 | 0.1682 |
| 32 | 63.24 | 0.9998 | 0.1682 |
| 48 | 59.94 | 0.9995 | 0.1680 |
| 64 | 57.28 | 0.9991 | 0.1680 |
