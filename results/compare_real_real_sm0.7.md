# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **synth_32 (32 images, 32768 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=0.7 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.0100**
- DCT-baseline (delta=32): **0.2390**
- DP-QIM: **0.1623**
- Ratio: DP-QIM is **1.47x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=32 | 63.12 | 0.9998 |
| DP-QIM | 63.44 | 0.9999 |
| Gap | 0.32 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 0.964 | -3.6 ✗ |
| jpeg_q90 | 0.998 | 0.764 | -23.4 ✗ |
| jpeg_q70 | 0.453 | 0.507 | +5.4 ★ |
| jpeg_q40 | 0.451 | 0.516 | +6.4 ★ |
| jpeg_q20 | 0.457 | 0.510 | +5.4 ★ |
| gauss_noise_.01 | 0.997 | 0.842 | -15.5 ✗ |
| gauss_noise_.03 | 0.887 | 0.720 | -16.7 ✗ |
| gauss_blur_1.0 | 0.455 | 0.778 | +32.3 ★ |
| gauss_blur_2.0 | 0.455 | 0.545 | +9.0 ★ |
| resize_0.5 | 0.455 | 0.738 | +28.3 ★ |
| resize_2.0 | 0.953 | 0.882 | -7.1 ✗ |
| rot_5 | 0.939 | 0.845 | -9.4 ✗ |
| crop_0.9 | 0.934 | 0.910 | -2.4 |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 74.40 | 1.0000 | 0.2389 |
| 12 | 70.47 | 1.0000 | 0.2389 |
| 16 | 69.47 | 0.9999 | 0.2389 |
| 20 | 67.46 | 0.9999 | 0.2390 |
| 24 | 65.57 | 0.9999 | 0.2389 |
| 32 | 63.12 | 0.9998 | 0.2390 |
| 48 | 59.64 | 0.9995 | 0.2389 |
| 64 | 56.95 | 0.9991 | 0.2389 |
