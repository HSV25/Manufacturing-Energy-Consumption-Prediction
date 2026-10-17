import csv
import logging
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from backend.app.database import SessionLocal
from backend.app.models.production_batch import ProductionBatch
from backend.ml.train_model import train_and_evaluate

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_CSV_PATH = BASE_DIR / "data" / "db_retraining_production_data.csv"
MIN_RECORDS_REQUIRED = 20


def export_and_retrain_from_database(min_records: int = MIN_RECORDS_REQUIRED):
    """
    Extracts validated actual production records from the SQLite database
    and retrains the energy prediction model.
    CRITICAL: Only records where actual_energy_consumed_kwh is recorded (not null)
    and strictly positive (> 0) are used. Predictions are NEVER used as targets.
    """
    db = SessionLocal()
    try:
        logger.info("Querying completed production batches with verified actual energy consumption...")
        batches = (
            db.query(ProductionBatch)
            .filter(
                ProductionBatch.actual_energy_consumed_kwh.isnot(None),
                ProductionBatch.actual_energy_consumed_kwh > 0,
            )
            .all()
        )

        logger.info(f"Found {len(batches)} eligible completed batches in database.")

        if len(batches) < min_records:
            logger.warning(
                f"Insufficient validated database records ({len(batches)} found, {min_records} required). "
                f"Retaining existing trained model pipeline."
            )
            return False

        # Build rows for retraining
        rows = []
        for b in batches:
            machine_type_name = b.machine_type.name if b.machine_type else "Unknown"
            shift_name = b.shift.name if b.shift else "Unknown"
            product_name = b.product.name if b.product else "Unknown"

            rows.append({
                "batch_number": b.batch_number,
                "product_name": product_name,
                "quantity": b.quantity,
                "machine_hours": b.machine_hours,
                "machine_type": machine_type_name,
                "shift": shift_name,
                "production_date": str(b.production_date),
                "actual_energy_consumed_kwh": b.actual_energy_consumed_kwh,
            })

        df = pd.DataFrame(rows)
        EXPORT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(EXPORT_CSV_PATH, index=False)
        logger.info(f"Exported {len(df)} validated production records to {EXPORT_CSV_PATH}")

        # Retrain pipeline using exported validated records
        logger.info("Executing retraining pipeline on database records...")
        metrics = train_and_evaluate(data_path=EXPORT_CSV_PATH)
        logger.info(f"Retraining complete! New evaluation metrics: {metrics['metrics']}")
        return True

    finally:
        db.close()


if __name__ == "__main__":
    export_and_retrain_from_database()
