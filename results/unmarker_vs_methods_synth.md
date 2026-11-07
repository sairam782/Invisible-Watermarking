# UnMarker-style attack: DCT baseline vs DP-QIM

Attacker reference: `synth_32` (32 images). 
Test: `synth_8` (8 images). Payload: 64 bits.

| Threshold | Jitter scale | DCT-baseline post-attack | DP-QIM post-attack | Attack PSNR |
|---|---|---|---|---|
| 1.5 | 0.3 | 0.982 | 0.916 | 45.17 |
| 1.5 | 0.5 | 0.902 | 0.912 | 40.92 |
| 1.5 | 1.0 | 0.734 | 0.910 **★** | 34.98 |
| 2.0 | 0.3 | 0.990 | 0.934 | 46.00 |
| 2.0 | 0.5 | 0.908 | 0.924 | 41.80 |
| 2.0 | 1.0 | 0.771 | 0.922 **★** | 35.87 |
| 3.0 | 0.3 | 0.988 | 0.926 | 46.54 |
| 3.0 | 0.5 | 0.928 | 0.910 | 42.36 |
| 3.0 | 1.0 | 0.779 | 0.906 **★** | 36.46 |
| 4.0 | 0.3 | 0.996 | 0.924 | 46.74 |
| 4.0 | 0.5 | 0.939 | 0.920 | 42.57 |
| 4.0 | 1.0 | 0.840 | 0.912 **★** | 36.67 |

**Best DP-QIM advantage**: threshold=1.5, jitter_scale=1.0 → DP-QIM survives at **0.910** vs baseline **0.734** (Δ = +17.6 pp).
