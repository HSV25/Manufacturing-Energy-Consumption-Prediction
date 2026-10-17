"""
Synthetic Manufacturing Energy Dataset Generator.

Generates physically grounded synthetic production data for training and evaluating
the supervised regression model.

Domain Physical Model:
    Total Energy (kWh) = (Base Power (kW) * Machine Hours + Specific Energy (kWh/unit) * Quantity)
                         * Shift Factor + Auxiliary Energy (kWh) + Noise

NOTICE:
    Records produced by this module are synthetic data generated for modeling,
    testing, and demonstration purposes. They reflect realistic physical engineering
    principles (idle power, variable cutting power, shift auxiliary lighting/HVAC)
    but do not represent actual proprietary factory sensor readings.
"""

import csv
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_OUTPUT_CSV = DATA_DIR / "sample_historical_production.csv"

# Domain Physical Constants
DEFAULT_MACHINE_SPECS: Dict[str, Dict[str, float]] = {
    "CNC": {"base_kw": 22.0, "kwh_per_unit": 1.20},
    "Lathe": {"base_kw": 14.0, "kwh_per_unit": 0.85},
    "Milling Machine": {"base_kw": 28.0, "kwh_per_unit": 1.65},
    "GEARBOX": {"base_kw": 18.5, "kwh_per_unit": 1.05},
}

DEFAULT_FALLBACK_SPEC: Dict[str, float] = {"base_kw": 18.0, "kwh_per_unit": 1.10}

SHIFT_SPECS: Dict[str, Dict[str, float]] = {
    "Morning": {"factor": 1.00, "aux_kwh": 5.0},
    "Afternoon": {"factor": 1.01, "aux_kwh": 6.0},
    "Evening": {"factor": 1.02, "aux_kwh": 8.0},
    "Night": {"factor": 1.05, "aux_kwh": 12.0},
}

SAMPLE_PRODUCTS = [
    "Industrial Gearbox Housing",
    "Hydraulic Valve Body",
    "Turbine Blade Mount",
    "Precision Drive Shaft",
    "Flange Connector",
]


def get_machine_spec(machine_name: str) -> Dict[str, float]:
    """Retrieves physical specifications for a machine type, falling back to typical factory defaults."""
    for known_name, spec in DEFAULT_MACHINE_SPECS.items():
        if known_name.lower() == machine_name.strip().lower():
            return spec
    # Return sensible default for newly registered custom machines
    return DEFAULT_FALLBACK_SPEC


def generate_synthetic_dataset(
    output_path: Optional[Path] = None,
    machine_types: Optional[List[str]] = None,
    shifts: Optional[List[str]] = None,
    num_samples: int = 1200,
    seed: int = 42,
) -> Path:
    """
    Generates a reproducible synthetic dataset for model training.

    Args:
        output_path: Path to save CSV file. Defaults to data/sample_historical_production.csv.
        machine_types: List of machine type names to include. Defaults to CNC, Lathe, Milling Machine.
        shifts: List of shifts to include. Defaults to Morning, Evening, Night.
        num_samples: Total number of records to generate.
        seed: Random seed for exact reproducibility.

    Returns:
        Path to the generated CSV file.
    """
    target_path = Path(output_path) if output_path else DEFAULT_OUTPUT_CSV
    target_path.parent.mkdir(parents=True, exist_ok=True)

    rng = random.Random(seed)

    if not machine_types:
        machine_types = list(DEFAULT_MACHINE_SPECS.keys())

    if not shifts:
        shifts = ["Morning", "Afternoon", "Evening", "Night"]

    records = []
    start_date = datetime(2025, 1, 1)

    for i in range(1, num_samples + 1):
        batch_number = f"BATCH-2025-{i:04d}"
        product_name = rng.choice(SAMPLE_PRODUCTS)
        m_type = rng.choice(machine_types)
        shift_name = rng.choice(shifts)

        # Machine hours between 2.0 and 16.0 hours (single or double shift run)
        machine_hours = round(rng.uniform(2.0, 16.0), 2)

        # Quantity produced proportional to hours (15-35 units/hour with variance)
        units_per_hour = rng.uniform(15.0, 35.0)
        quantity = int(round(machine_hours * units_per_hour))
        quantity = max(10, min(quantity, 600))

        # Physical energy formulation
        spec = get_machine_spec(m_type)
        shift_info = SHIFT_SPECS.get(shift_name, {"factor": 1.00, "aux_kwh": 6.0})

        base_energy = spec["base_kw"] * machine_hours
        variable_energy = spec["kwh_per_unit"] * quantity
        aux_energy = shift_info["aux_kwh"]

        raw_energy = (base_energy + variable_energy) * shift_info["factor"] + aux_energy
        noise = rng.gauss(0, 8.0)  # Shop floor thermal and equipment noise

        actual_energy_kwh = round(max(15.0, raw_energy + noise), 2)

        # Production date spread over past 6 months
        days_offset = rng.randint(0, 180)
        production_date = (start_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")

        records.append({
            "batch_number": batch_number,
            "product_name": product_name,
            "quantity": quantity,
            "machine_hours": machine_hours,
            "machine_type": m_type,
            "shift": shift_name,
            "production_date": production_date,
            "actual_energy_consumed_kwh": actual_energy_kwh,
        })

    fieldnames = [
        "batch_number",
        "product_name",
        "quantity",
        "machine_hours",
        "machine_type",
        "shift",
        "production_date",
        "actual_energy_consumed_kwh",
    ]

    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    logger.info(f"Generated {len(records)} synthetic historical records at: {target_path}")
    return target_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_synthetic_dataset()
