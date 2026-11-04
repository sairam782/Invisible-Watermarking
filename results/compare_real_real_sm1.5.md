# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **real (9 images, 32614 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=1.5 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.1184**
- DCT-baseline (delta=64): **0.1682**
- DP-QIM: **0.1747**
- Ratio: DP-QIM is **0.96x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=64 | 57.30 | 0.9991 |
| DP-QIM | 57.79 | 0.9995 |
| Gap | 0.50 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 0.993 | -0.7 |
| jpeg_q90 | 1.000 | 0.845 | -15.5 ✗ |
| jpeg_q70 | 0.997 | 0.644 | -35.2 ✗ |
| jpeg_q40 | 0.497 | 0.559 | +6.2 ★ |
| jpeg_q20 | 0.497 | 0.514 | +1.7 |
| gauss_noise_.01 | 0.997 | 0.896 | -10.1 ✗ |
| gauss_noise_.03 | 0.995 | 0.811 | -18.4 ✗ |
| gauss_blur_1.0 | 0.498 | 0.832 | +33.3 ★ |
| gauss_blur_2.0 | 0.497 | 0.583 | +8.7 ★ |
| resize_0.5 | 0.497 | 0.806 | +30.9 ★ |
| resize_2.0 | 0.986 | 0.932 | -5.4 ✗ |
| rot_5 | 0.977 | 0.915 | -6.2 ✗ |
| crop_0.9 | 0.941 | 0.939 | -0.2 |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 74.29 | 1.0000 | 0.1682 |
| 12 | 70.75 | 1.0000 | 0.1682 |
| 16 | 69.70 | 1.0000 | 0.1682 |
| 20 | 67.74 | 0.9999 | 0.1682 |
| 24 | 65.81 | 0.9999 | 0.1682 |
| 32 | 63.48 | 0.9998 | 0.1682 |
| 48 | 60.16 | 0.9995 | 0.1682 |
| 64 | 57.30 | 0.9991 | 0.1682 |
