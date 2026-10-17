"""
Model Training and Safe Lifecycle Pipeline.

Trains the supervised Linear Regression pipeline with StandardScaler and OneHotEncoder.
Features:
- Validates data integrity and numeric ranges before training.
- Fits preprocessing strictly on training data (train_test_split 80/20).
- Calculates MAE, RMSE, and R2 on held-out test data.
- Validates candidate model quality (R2 threshold and inference check) before replacing artifacts.
- Atomic artifact replacement with automatic rollback on failure to prevent partial or corrupted models.
- Reloads in-memory predictor instance upon successful training.
"""

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA_PATH = BASE_DIR / "data" / "sample_historical_production.csv"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DEFAULT_MODEL_PATH = ARTIFACTS_DIR / "model.joblib"
DEFAULT_METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

FEATURE_NUMERIC = ["quantity", "machine_hours"]
FEATURE_CATEGORICAL = ["machine_type", "shift"]
TARGET_COLUMN = "actual_energy_consumed_kwh"
MODEL_VERSION = "v1.1.0"


def load_and_validate_data(csv_path: Path) -> pd.DataFrame:
    """Loads CSV and validates that required columns and valid numeric ranges exist."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Training data file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    logger.info(f"Loaded dataset with {len(df)} rows from {csv_path}")

    required_cols = FEATURE_NUMERIC + FEATURE_CATEGORICAL + [TARGET_COLUMN]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset is missing required columns: {missing_cols}")

    # Drop rows with nulls in required columns
    initial_len = len(df)
    df = df.dropna(subset=required_cols)
    dropped_nulls = initial_len - len(df)
    if dropped_nulls > 0:
        logger.warning(f"Dropped {dropped_nulls} rows with null values")

    # Validate numeric types and ranges
    for col in FEATURE_NUMERIC + [TARGET_COLUMN]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop invalid NaN converted rows
    df = df.dropna(subset=FEATURE_NUMERIC + [TARGET_COLUMN])

    # Range validations
    valid_mask = (
        (df["quantity"] > 0)
        & (df["machine_hours"] > 0)
        & (df[TARGET_COLUMN] > 0)
        & (df["machine_type"].astype(str).str.strip() != "")
        & (df["shift"].astype(str).str.strip() != "")
    )
    df = df[valid_mask].copy()

    if len(df) < 50:
        raise ValueError(f"Insufficient training data after validation. Only {len(df)} valid records found.")

    logger.info(f"Dataset validated successfully: {len(df)} clean records available")
    return df


def build_pipeline() -> Pipeline:
    """Builds a scikit-learn Pipeline with ColumnTransformer for preprocessing and LinearRegression."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), FEATURE_NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), FEATURE_CATEGORICAL),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", LinearRegression()),
        ]
    )
    return pipeline


def validate_candidate_model(pipeline: Pipeline, df: pd.DataFrame, r2: float) -> None:
    """
    Validates candidate model quality before writing active artifact.
    Ensures R2 score meets minimum standard and model produces positive, finite predictions.
    """
    if r2 < 0.70:
        raise ValueError(f"Candidate model validation failed: R² score ({r2:.4f}) is below acceptable threshold (0.70).")

    # Test inference across all unique machine types in dataset
    unique_machines = df["machine_type"].dropna().unique()
    unique_shifts = df["shift"].dropna().unique()

    for m in unique_machines:
        test_df = pd.DataFrame([{
            "quantity": 100.0,
            "machine_hours": 8.0,
            "machine_type": m,
            "shift": unique_shifts[0] if len(unique_shifts) > 0 else "Morning",
        }])
        pred = pipeline.predict(test_df)
        if pred is None or len(pred) == 0:
            raise ValueError(f"Candidate model returned empty prediction for machine type '{m}'.")
        val = float(pred[0])
        if np.isnan(val) or np.isinf(val) or val <= 0:
            raise ValueError(f"Candidate model returned invalid prediction {val} for machine type '{m}'.")

    logger.info(f"Candidate model successfully passed verification checks on {len(unique_machines)} machine types.")


def train_and_evaluate(
    data_path: Path = DEFAULT_DATA_PATH,
    model_save_path: Path = DEFAULT_MODEL_PATH,
    metrics_save_path: Path = DEFAULT_METRICS_PATH,
    test_size: float = 0.2,
    random_state: int = 42,
    model_version: str = MODEL_VERSION,
) -> dict:
    """
    Trains the regression pipeline, evaluates metrics, validates the candidate model,
    and atomically saves model artifacts with rollback capability.
    """
    data_path = Path(data_path)
    model_save_path = Path(model_save_path)
    metrics_save_path = Path(metrics_save_path)

    df = load_and_validate_data(data_path)

    X = df[FEATURE_NUMERIC + FEATURE_CATEGORICAL]
    y = df[TARGET_COLUMN]

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )
    logger.info(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples")

    # Fit pipeline
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    # Predict on test set
    y_pred = pipeline.predict(X_test)

    # Evaluate metrics
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2 = float(r2_score(y_test, y_pred))

    logger.info(f"Candidate Model Evaluation Results:")
    logger.info(f" - MAE:  {mae:.3f} kWh")
    logger.info(f" - RMSE: {rmse:.3f} kWh")
    logger.info(f" - R²:   {r2:.4f}")

    # Validate candidate model
    validate_candidate_model(pipeline, df, r2)

    # Ensure artifacts directory exists
    model_save_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_save_path.parent.mkdir(parents=True, exist_ok=True)

    # Prepare temporary file paths for atomic swap
    tmp_model_path = model_save_path.with_suffix(".tmp")
    tmp_metrics_path = metrics_save_path.with_suffix(".tmp")
    bak_model_path = model_save_path.with_suffix(".bak")
    bak_metrics_path = metrics_save_path.with_suffix(".bak")

    # Save metrics metadata
    known_machine_types = sorted(df["machine_type"].dropna().unique().tolist())
    known_shifts = sorted(df["shift"].dropna().unique().tolist())

    import sklearn

    metrics_payload = {
        "model_name": "Linear Regression Pipeline",
        "model_version": model_version,
        "algorithm": "LinearRegression with StandardScaler and OneHotEncoder",
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics": {
            "mae_kwh": round(mae, 3),
            "rmse_kwh": round(rmse, 3),
            "r2_score": round(r2, 4),
        },
        "features": {
            "numeric": FEATURE_NUMERIC,
            "categorical": FEATURE_CATEGORICAL,
        },
        "known_categories": {
            "machine_types": known_machine_types,
            "shifts": known_shifts,
        },
        "data_source": str(data_path.name),
        "target": TARGET_COLUMN,
    }

    try:
        # Step 1: Write candidate files to temporary targets
        joblib.dump(pipeline, tmp_model_path)
        with open(tmp_metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics_payload, f, indent=2)

        # Step 2: Backup existing active model if present
        if model_save_path.exists():
            shutil.copy2(model_save_path, bak_model_path)
        if metrics_save_path.exists():
            shutil.copy2(metrics_save_path, bak_metrics_path)

        # Step 3: Atomic rename to replace active artifacts
        os.replace(tmp_model_path, model_save_path)
        os.replace(tmp_metrics_path, metrics_save_path)

        # Step 4: Remove backup files upon successful replacement
        if bak_model_path.exists():
            bak_model_path.unlink()
        if bak_metrics_path.exists():
            bak_metrics_path.unlink()

        logger.info(f"Model artifact successfully activated at: {model_save_path}")
        logger.info(f"Metrics metadata successfully saved to: {metrics_save_path}")

        # Step 5: Reload in-memory predictor instance if running in same process
        try:
            from backend.ml.predict import predictor
            predictor.reload()
            logger.info("In-memory EnergyPredictor successfully reloaded new model.")
        except Exception as e:
            logger.debug(f"Predictor reload notification skipped: {e}")

        return metrics_payload

    except Exception as e:
        logger.error(f"Error activating candidate model: {e}. Executing rollback...")
        # Clean up temporary files
        if tmp_model_path.exists():
            tmp_model_path.unlink()
        if tmp_metrics_path.exists():
            tmp_metrics_path.unlink()
        # Restore backup if active was removed
        if bak_model_path.exists() and not model_save_path.exists():
            os.replace(bak_model_path, model_save_path)
        if bak_metrics_path.exists() and not metrics_save_path.exists():
            os.replace(bak_metrics_path, metrics_save_path)
        raise RuntimeError(f"Model training and activation failed: {e}") from e


def retrain_with_categories(
    machine_types: List[str],
    shifts: Optional[List[str]] = None,
    num_samples: int = 1200,
    seed: int = 42,
) -> dict:
    """
    Generates a fresh synthetic dataset including the specified machine types and shifts,
    trains the pipeline, validates candidate quality, and activates the new model.
    """
    from backend.ml.dataset import generate_synthetic_dataset

    logger.info(f"Regenerating training dataset for machine types: {machine_types}, shifts: {shifts}")
    data_path = generate_synthetic_dataset(
        machine_types=machine_types,
        shifts=shifts,
        num_samples=num_samples,
        seed=seed,
    )
    return train_and_evaluate(data_path=data_path)


def retrain_with_machine_types(
    machine_types: List[str],
    shifts: Optional[List[str]] = None,
    num_samples: int = 1200,
    seed: int = 42,
) -> dict:
    """Backward compatible wrapper around retrain_with_categories."""
    return retrain_with_categories(
        machine_types=machine_types,
        shifts=shifts,
        num_samples=num_samples,
        seed=seed,
    )


if __name__ == "__main__":
    train_and_evaluate()
