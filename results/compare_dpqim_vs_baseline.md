# DCT baseline vs DP-QIM — matched-PSNR head-to-head

Position: uv=(3, 3), payload=64 bits, 8 test photos.

## Undetectability (KS vs natural, measured on watermarked coeffs only)

- Natural-vs-natural reference: **0.0107**
- DCT-baseline (delta=24): **0.0969**
- DP-QIM: **0.1947**
- DP-QIM is **0.50x more undetectable**

## Fidelity

| Method | PSNR | SSIM |
|---|---|---|
| DCT-baseline delta=24 | 61.17 | 0.9998 |
| DP-QIM | 61.34 | 0.9998 |
| Gap | 0.16 dB | |

## Bit accuracy per attack

| Attack | DCT-baseline | DP-QIM | Δ (pp) |
|---|---|---|---|
| identity | 1.000 | 1.000 | +0.0 |
| jpeg_q90 | 1.000 | 0.920 | -8.0 ✗ |
| jpeg_q70 | 0.504 | 0.527 | +2.3 |
| jpeg_q40 | 0.529 | 0.500 | -2.9 |
| jpeg_q20 | 0.529 | 0.525 | -0.4 |
| gauss_noise_.01 | 0.996 | 0.941 | -5.5 ✗ |
| gauss_noise_.03 | 0.713 | 0.822 | +10.9 ★ |
| gauss_blur_1.0 | 0.529 | 0.883 | +35.4 ★ |
| gauss_blur_2.0 | 0.529 | 0.561 | +3.1 ★ |
| resize_0.5 | 0.529 | 0.877 | +34.8 ★ |
| resize_2.0 | 0.988 | 0.965 | -2.3 |
| rot_5 | 0.963 | 0.932 | -3.1 ✗ |
| crop_0.9 | 0.936 | 0.957 | +2.1 |
