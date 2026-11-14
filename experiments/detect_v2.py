"""Compatibility entry point: v2 detector evaluation is superseded.

The original implementation remains in git history at bf2f3b0. New runs use
training-only v3 evaluation and write results/v3, never results/v2.
"""
from experiments.detect_v3 import main

if __name__ == "__main__":
    main()
