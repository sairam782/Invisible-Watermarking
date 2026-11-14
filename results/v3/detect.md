# Corrected v3 detectability

43 crops / 14 sources; training-only outer-fold fitting and fidelity calibration.
AUC: test-crop-weighted mean within-fold AUC; conditional source-bootstrap CIs.

| Bits | Margin | DP PSNR | QIM PSNR | DP learned AUC | QIM learned AUC | DP peak | QIM peak |
|---|---|---|---|---|---|---|---|
| 64.000 | 1.000 | 53.271 | 53.684 | 0.655 | 0.998 | 0.465 | 0.640 |
| 64.000 | 2.000 | 53.360 | 53.660 | 0.647 | 0.947 | 0.468 | 0.644 |
| 256.000 | 1.000 | 47.231 | 47.418 | 0.785 | 1.000 | 0.444 | 0.884 |
| 256.000 | 2.000 | 46.942 | 47.118 | 0.836 | 1.000 | 0.495 | 0.833 |
| 1024.000 | 1.000 | 41.268 | 41.417 | 0.877 | 1.000 | 0.599 | 0.952 |
| 1024.000 | 2.000 | 40.959 | 41.073 | 0.955 | 1.000 | 0.624 | 0.969 |
