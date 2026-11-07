# UnMarker-style attack: DCT baseline vs DP-QIM

Attacker reference: `real` (9 images). 
Test: `real` (9 images). Payload: 64 bits.

| Threshold | Jitter scale | DCT-baseline post-attack | DP-QIM post-attack | Attack PSNR |
|---|---|---|---|---|
| 1.5 | 0.3 | 0.924 | 0.858 | 35.10 |
| 1.5 | 0.5 | 0.845 | 0.837 | 30.73 |
| 1.5 | 1.0 | 0.736 | 0.823 **★** | 24.81 |
| 2.0 | 0.3 | 0.920 | 0.908 | 36.30 |
| 2.0 | 0.5 | 0.825 | 0.896 **★** | 31.95 |
| 2.0 | 1.0 | 0.764 | 0.887 **★** | 26.03 |
| 3.0 | 0.3 | 0.934 | 0.905 | 38.01 |
| 3.0 | 0.5 | 0.865 | 0.894 **★** | 33.69 |
| 3.0 | 1.0 | 0.842 | 0.880 **★** | 27.78 |
| 4.0 | 0.3 | 0.962 | 0.922 | 38.99 |
| 4.0 | 0.5 | 0.922 | 0.918 | 34.70 |
| 4.0 | 1.0 | 0.920 | 0.913 | 28.79 |

**Best DP-QIM advantage**: threshold=2.0, jitter_scale=1.0 → DP-QIM survives at **0.887** vs baseline **0.764** (Δ = +12.3 pp).
