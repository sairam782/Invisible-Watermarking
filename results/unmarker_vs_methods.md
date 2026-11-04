# UnMarker-style attack: DCT baseline vs DP-QIM

Attacker reference: `synth_32` (32 images). 
Test: `synth_8` (8 images). Payload: 64 bits.

| Threshold | Jitter scale | DCT-baseline post-attack | DP-QIM post-attack | Attack PSNR |
|---|---|---|---|---|
| 1.5 | 0.3 | 0.977 | 0.908 | 45.17 |
| 1.5 | 0.5 | 0.898 | 0.898 | 40.92 |
| 1.5 | 1.0 | 0.777 | 0.893 **★** | 34.98 |
| 2.0 | 0.3 | 0.986 | 0.926 | 46.01 |
| 2.0 | 0.5 | 0.910 | 0.920 | 41.80 |
| 2.0 | 1.0 | 0.771 | 0.914 **★** | 35.88 |
| 3.0 | 0.3 | 0.984 | 0.916 | 46.55 |
| 3.0 | 0.5 | 0.938 | 0.908 | 42.37 |
| 3.0 | 1.0 | 0.865 | 0.906 **★** | 36.46 |
| 4.0 | 0.3 | 0.990 | 0.934 | 46.74 |
| 4.0 | 0.5 | 0.943 | 0.930 | 42.57 |
| 4.0 | 1.0 | 0.848 | 0.922 **★** | 36.67 |

**Best DP-QIM advantage**: threshold=2.0, jitter_scale=1.0 → DP-QIM survives at **0.914** vs baseline **0.771** (Δ = +14.3 pp).
