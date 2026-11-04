# Real-dataset head-to-head: DCT baseline vs DP-QIM

- Dataset: **real**
- Training (for CDF + sample pools): **real (9 images, 32614 blocks)**
- DP-QIM operating point: `uv=(3, 3) M=1 sm=0.7 pool=128`
- Payload: 64 bits per image · uv=(3,3)

## Undetectability (KS to natural, watermarked coeffs only)

- Natural-vs-natural reference: **0.1184**
- DCT-baseline (delta=48): **0.1682**
- DP-QIM: **0.1442**
- Ratio: DP-QIM is **1.17x more undetectable**

## Fidelity

| Method | PSNR (dB) | SSIM |
|---|---|---|
| DCT-baseline delta=48 | 60.21 | 0.9996 |
| DP-QIM | 60.14 | 0.9998 |
| Gap | 0.08 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 0.955 | -4.5 ✗ |
| jpeg_q90 | 0.993 | 0.753 | -24.0 ✗ |
| jpeg_q70 | 0.965 | 0.618 | -34.7 ✗ |
| jpeg_q40 | 0.483 | 0.578 | +9.5 ★ |
| jpeg_q20 | 0.502 | 0.491 | -1.0 |
| gauss_noise_.01 | 0.993 | 0.868 | -12.5 ✗ |
| gauss_noise_.03 | 0.981 | 0.783 | -19.8 ✗ |
| gauss_blur_1.0 | 0.507 | 0.783 | +27.6 ★ |
| gauss_blur_2.0 | 0.502 | 0.540 | +3.8 ★ |
| resize_0.5 | 0.502 | 0.747 | +24.5 ★ |
| resize_2.0 | 0.979 | 0.885 | -9.4 ✗ |
| rot_5 | 0.965 | 0.865 | -10.1 ✗ |
| crop_0.9 | 0.943 | 0.899 | -4.3 ✗ |

## Full baseline sweep

| delta | PSNR | SSIM | KS |
|---|---|---|---|
| 8 | 74.23 | 1.0000 | 0.1682 |
| 12 | 70.92 | 1.0000 | 0.1682 |
| 16 | 69.98 | 1.0000 | 0.1682 |
| 20 | 67.96 | 0.9999 | 0.1682 |
| 24 | 65.92 | 0.9999 | 0.1682 |
| 32 | 63.52 | 0.9998 | 0.1682 |
| 48 | 60.21 | 0.9996 | 0.1682 |
| 64 | 57.49 | 0.9992 | 0.1682 |
