"""
Script to generate sample historical manufacturing data for model training.
Delegates to backend.ml.dataset generator.
"""

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from backend.ml.dataset import generate_synthetic_dataset, DEFAULT_OUTPUT_CSV


def generate_data(num_samples: int = 1200, seed: int = 42):
    output_path = generate_synthetic_dataset(
        output_path=DEFAULT_OUTPUT_CSV,
        num_samples=num_samples,
        seed=seed,
    )
    print(f"Generated {num_samples} synthetic historical records at: {output_path}")


if __name__ == "__main__":
    generate_data()
