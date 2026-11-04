# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **real (9 images, 32614 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=3.0 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.1184**
- DCT-baseline (delta=64): **0.1682**
- DP-QIM: **0.2151**
- Ratio: DP-QIM is **0.78x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=64 | 57.57 | 0.9992 |
| DP-QIM | 57.32 | 0.9995 |
| Gap | 0.25 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 1.000 | +0.0 |
| jpeg_q90 | 1.000 | 0.865 | -13.5 ✗ |
| jpeg_q70 | 0.997 | 0.710 | -28.6 ✗ |
| jpeg_q40 | 0.497 | 0.589 | +9.2 ★ |
| jpeg_q20 | 0.498 | 0.536 | +3.8 ★ |
| gauss_noise_.01 | 0.997 | 0.917 | -8.0 ✗ |
| gauss_noise_.03 | 0.995 | 0.851 | -14.4 ✗ |
| gauss_blur_1.0 | 0.497 | 0.845 | +34.9 ★ |
| gauss_blur_2.0 | 0.498 | 0.594 | +9.5 ★ |
| resize_0.5 | 0.498 | 0.828 | +33.0 ★ |
| resize_2.0 | 0.983 | 0.962 | -2.1 |
| rot_5 | 0.984 | 0.946 | -3.8 ✗ |
| crop_0.9 | 0.951 | 0.944 | -0.7 |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 74.33 | 1.0000 | 0.1682 |
| 12 | 70.98 | 1.0000 | 0.1682 |
| 16 | 70.01 | 1.0000 | 0.1682 |
| 20 | 67.79 | 0.9999 | 0.1682 |
| 24 | 65.96 | 0.9999 | 0.1682 |
| 32 | 63.57 | 0.9998 | 0.1682 |
| 48 | 60.46 | 0.9996 | 0.1682 |
| 64 | 57.57 | 0.9992 | 0.1682 |
