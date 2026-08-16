# DCT Baseline — payload=64 bits, delta=16.0

Fidelity (cover vs watermarked, averaged over 8 images):
- PSNR: **64.46 dB**  (min 63.65)
- SSIM: **1.0000**

| Attack | Mean bit accuracy |
|---|---|
| identity | 1.0000 |
| jpeg_q90 | 0.8379 |
| jpeg_q70 | 0.4902 |
| jpeg_q40 | 0.4902 |
| jpeg_q20 | 0.4902 |
| gauss_noise_.01 | 0.9238 |
| gauss_noise_.03 | 0.5664 |
| gauss_blur_1.0 | 0.4883 |
| gauss_blur_2.0 | 0.4902 |
| resize_0.5 | 0.4902 |
| resize_2.0 | 0.8477 |
| rot_5 | 0.8711 |
| crop_0.9 | 0.9414 |
