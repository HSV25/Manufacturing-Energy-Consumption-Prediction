import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import joblib
import pandas as pd
import sklearn
from backend.app.config import MODEL_PATH, METRICS_PATH

logger = logging.getLogger(__name__)


class EnergyPredictor:
    """Predictor service encapsulating the scikit-learn pipeline for electricity estimation."""

    def __init__(self, model_path: Optional[str] = None, metrics_path: Optional[str] = None):
        self.model_path = Path(model_path or MODEL_PATH)
        self.metrics_path = Path(metrics_path or METRICS_PATH)
        self.pipeline = None
        self.metrics: Dict[str, Any] = {}
        self.model_version = "v1.0.0"
        self.load_error: Optional[str] = None
        self.load_model()

    def reload(self) -> bool:
        """Forces reloading of the pipeline and metrics from disk."""
        return self.load_model()

    def load_model(self) -> bool:
        """
        Loads and validates the fitted pipeline and metrics metadata.
        Explicitly verifies compatibility with the current scikit-learn runtime.
        """
        self.load_error = None

        if not self.model_path.exists():
            self.load_error = (
                f"Model artifact not found at {self.model_path}. "
                "Please run 'python backend/ml/train_model.py' to train and save the pipeline."
            )
            logger.warning(self.load_error)
            self.pipeline = None
            return False

        # Load metrics metadata if present
        if self.metrics_path.exists():
            try:
                with open(self.metrics_path, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
                    self.model_version = self.metrics.get("model_version", "v1.0.0")
            except Exception as e:
                logger.warning(f"Could not read metrics metadata from {self.metrics_path}: {e}")

        # Attempt to load model artifact
        try:
            loaded_pipeline = joblib.load(self.model_path)

            # Determine supported categories for runtime verification
            known_cats = self.metrics.get("known_categories", {})
            test_m = known_cats.get("machine_types", ["CNC"])[0]
            test_s = known_cats.get("shifts", ["Morning"])[0]

            test_df = pd.DataFrame(
                [{"quantity": 100.0, "machine_hours": 8.0, "machine_type": test_m, "shift": test_s}]
            )
            test_val = loaded_pipeline.predict(test_df)
            if test_val is None or len(test_val) == 0:
                raise ValueError("Verification prediction returned empty result.")

            self.pipeline = loaded_pipeline
            self.load_error = None
            logger.info(f"Loaded and verified trained ML pipeline from {self.model_path}")
            return True

        except Exception as e:
            saved_ver = self.metrics.get("sklearn_version", "1.6.1")
            self.load_error = (
                f"Incompatible or invalid model artifact at {self.model_path}: {str(e)}. "
                f"Current scikit-learn is {sklearn.__version__} (model was trained with {saved_ver}). "
                "Run 'python backend/ml/train_model.py' to regenerate the model artifact."
            )
            logger.error(self.load_error)
            self.pipeline = None
            return False

    def is_ready(self) -> bool:
        return self.pipeline is not None

    def get_supported_machine_types(self) -> List[str]:
        """Returns the list of machine types supported by the active model."""
        known_cats = self.metrics.get("known_categories", {})
        machines = known_cats.get("machine_types", [])
        if not machines and self.pipeline is not None:
            # Fallback: extract directly from OneHotEncoder if available
            try:
                cat_encoder = self.pipeline.named_steps["preprocessor"].named_transformers_["cat"]
                machines = list(cat_encoder.categories_[0])
            except Exception:
                machines = ["CNC", "Lathe", "Milling Machine"]
        return machines

    def get_supported_shifts(self) -> List[str]:
        """Returns the list of shifts supported by the active model."""
        known_cats = self.metrics.get("known_categories", {})
        shifts = known_cats.get("shifts", [])
        if not shifts and self.pipeline is not None:
            try:
                cat_encoder = self.pipeline.named_steps["preprocessor"].named_transformers_["cat"]
                shifts = list(cat_encoder.categories_[1])
            except Exception:
                shifts = ["Morning", "Evening", "Night"]
        return shifts

    def is_machine_type_supported(self, machine_type: str) -> bool:
        """Checks if a machine type name is supported by the active model."""
        clean = str(machine_type).strip().lower()
        return any(m.lower() == clean for m in self.get_supported_machine_types())

    def is_shift_supported(self, shift: str) -> bool:
        """Checks if a shift name is supported by the active model."""
        clean = str(shift).strip().lower()
        return any(s.lower() == clean for s in self.get_supported_shifts())

    def get_info(self) -> Dict[str, Any]:
        return {
            "is_trained": self.is_ready(),
            "model_version": self.model_version,
            "metrics": self.metrics.get("metrics", {}),
            "supported_machine_types": self.get_supported_machine_types(),
            "supported_shifts": self.get_supported_shifts(),
            "known_categories": self.metrics.get("known_categories", {}),
            "trained_at": self.metrics.get("trained_at"),
            "sklearn_version": sklearn.__version__,
            "artifact_sklearn_version": self.metrics.get("sklearn_version"),
            "error": self.load_error,
        }

    def predict(
        self,
        quantity: float,
        machine_hours: float,
        machine_type: str,
        shift: str,
    ) -> Dict[str, Any]:
        """
        Validates inputs and computes estimated energy in kWh using the fitted regression pipeline.
        """
        if not self.is_ready():
            # Try reloading once in case artifact was newly generated
            if not self.load_model():
                raise RuntimeError(
                    self.load_error
                    or "Energy prediction model is not trained or could not be loaded. "
                    "Please run 'python backend/ml/train_model.py'."
                )

        # Numerical input validations
        if quantity is None or quantity <= 0:
            raise ValueError(f"Quantity must be a positive number greater than 0, received: {quantity}")

        if machine_hours is None or machine_hours <= 0:
            raise ValueError(f"Machine hours must be a positive number greater than 0, received: {machine_hours}")

        if not machine_type or not str(machine_type).strip():
            raise ValueError("Machine type must not be blank")

        if not shift or not str(shift).strip():
            raise ValueError("Shift must not be blank")

        machine_type_clean = str(machine_type).strip()
        shift_clean = str(shift).strip()

        # Check known categories if metadata available
        known_machines = self.get_supported_machine_types()
        known_shifts = self.get_supported_shifts()

        if known_machines and not self.is_machine_type_supported(machine_type_clean):
            raise ValueError(
                f"Unrecognized machine type '{machine_type}'. "
                f"Machine type '{machine_type}' is not represented in the active ML model ({self.model_version}). "
                f"Currently supported machine types are: {', '.join(known_machines)}. "
                "Retraining the model with representative data is required to predict for this category."
            )

        # Normalize canonical casing for known machines
        canonical_machine = next((m for m in known_machines if m.lower() == machine_type_clean.lower()), machine_type_clean)

        if known_shifts and not self.is_shift_supported(shift_clean):
            raise ValueError(
                f"Unrecognized shift '{shift}'. "
                f"Shift '{shift}' is not represented in the active ML model ({self.model_version}). "
                f"Currently supported shifts are: {', '.join(known_shifts)}."
            )

        canonical_shift = next((s for s in known_shifts if s.lower() == shift_clean.lower()), shift_clean)

        # Build feature DataFrame matching pipeline input structure
        input_df = pd.DataFrame(
            [
                {
                    "quantity": float(quantity),
                    "machine_hours": float(machine_hours),
                    "machine_type": canonical_machine,
                    "shift": canonical_shift,
                }
            ]
        )

        try:
            raw_prediction = self.pipeline.predict(input_df)[0]
        except Exception as e:
            logger.error(f"Prediction inference failed: {e}")
            raise RuntimeError(f"Error during model inference: {str(e)}")

        # Enforce physical validity: Energy cannot be negative
        estimated_energy = max(0.0, float(raw_prediction))
        estimated_energy = round(estimated_energy, 2)

        return {
            "estimated_energy": estimated_energy,
            "unit": "kWh",
            "model_version": self.model_version,
            "input_features": {
                "quantity": quantity,
                "machine_hours": machine_hours,
                "machine_type": canonical_machine,
                "shift": canonical_shift,
            },
        }


# Singleton instance for application use
predictor = EnergyPredictor()
