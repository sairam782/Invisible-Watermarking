# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **real (9 images, 32614 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=2.0 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.1184**
- DCT-baseline (delta=64): **0.1680**
- DP-QIM: **0.1904**
- Ratio: DP-QIM is **0.88x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=64 | 57.27 | 0.9991 |
| DP-QIM | 57.89 | 0.9996 |
| Gap | 0.62 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 1.000 | +0.0 |
| jpeg_q90 | 1.000 | 0.800 | -20.0 ✗ |
| jpeg_q70 | 0.997 | 0.681 | -31.6 ✗ |
| jpeg_q40 | 0.503 | 0.594 | +9.0 ★ |
| jpeg_q20 | 0.505 | 0.540 | +3.5 ★ |
| gauss_noise_.01 | 0.997 | 0.901 | -9.5 ✗ |
| gauss_noise_.03 | 0.995 | 0.828 | -16.7 ✗ |
| gauss_blur_1.0 | 0.503 | 0.840 | +33.7 ★ |
| gauss_blur_2.0 | 0.505 | 0.576 | +7.1 ★ |
| resize_0.5 | 0.505 | 0.800 | +29.5 ★ |
| resize_2.0 | 0.990 | 0.943 | -4.7 ✗ |
| rot_5 | 0.976 | 0.915 | -6.1 ✗ |
| crop_0.9 | 0.951 | 0.943 | -0.9 |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 73.96 | 1.0000 | 0.1682 |
| 12 | 70.54 | 1.0000 | 0.1682 |
| 16 | 69.54 | 0.9999 | 0.1682 |
| 20 | 67.48 | 0.9999 | 0.1682 |
| 24 | 65.60 | 0.9999 | 0.1682 |
| 32 | 63.31 | 0.9997 | 0.1682 |
| 48 | 59.95 | 0.9995 | 0.1680 |
| 64 | 57.27 | 0.9991 | 0.1680 |
