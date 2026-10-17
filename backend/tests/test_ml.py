import math
from pathlib import Path
import pytest
from backend.ml.train_model import train_and_evaluate, DEFAULT_DATA_PATH
from backend.ml.predict import EnergyPredictor, predictor


def test_model_training_and_artifacts_generation(tmp_path):
    """Verify that training pipeline executes cleanly and outputs valid model & metrics artifacts."""
    test_model_path = tmp_path / "model.joblib"
    test_metrics_path = tmp_path / "metrics.json"

    metrics = train_and_evaluate(
        data_path=DEFAULT_DATA_PATH,
        model_save_path=test_model_path,
        metrics_save_path=test_metrics_path,
        test_size=0.2,
        random_state=42,
    )

    assert test_model_path.exists(), "Model artifact was not saved"
    assert test_metrics_path.exists(), "Metrics metadata was not saved"
    assert "metrics" in metrics
    assert "mae_kwh" in metrics["metrics"]
    assert "rmse_kwh" in metrics["metrics"]
    assert "r2_score" in metrics["metrics"]
    assert metrics["metrics"]["r2_score"] > 0.8, "R2 score should be substantial"


def test_prediction_output_is_numeric_and_finite():
    """Verify prediction output is a positive, finite number."""
    result = predictor.predict(quantity=100, machine_hours=8, machine_type="CNC", shift="Morning")

    assert isinstance(result, dict)
    assert "estimated_energy" in result
    energy = result["estimated_energy"]
    assert isinstance(energy, float)
    assert math.isfinite(energy)
    assert energy > 0.0
    assert result["unit"] == "kWh"


def test_predictions_are_not_hardcoded():
    """Verify that varying inputs produce varying, model-inferred outputs."""
    res_low = predictor.predict(quantity=50, machine_hours=4, machine_type="Lathe", shift="Morning")
    res_high = predictor.predict(quantity=300, machine_hours=14, machine_type="Milling Machine", shift="Night")

    assert res_low["estimated_energy"] != res_high["estimated_energy"]
    assert res_high["estimated_energy"] > res_low["estimated_energy"]

    # Changing only quantity should change predicted energy
    res_q1 = predictor.predict(quantity=100, machine_hours=8, machine_type="CNC", shift="Morning")
    res_q2 = predictor.predict(quantity=200, machine_hours=8, machine_type="CNC", shift="Morning")
    assert res_q2["estimated_energy"] > res_q1["estimated_energy"]

    # Changing only machine hours should change predicted energy
    res_h1 = predictor.predict(quantity=100, machine_hours=4, machine_type="CNC", shift="Morning")
    res_h2 = predictor.predict(quantity=100, machine_hours=10, machine_type="CNC", shift="Morning")
    assert res_h2["estimated_energy"] > res_h1["estimated_energy"]


def test_machine_type_variation():
    """Different machine types should yield different energy consumption due to different baselines."""
    res_lathe = predictor.predict(quantity=100, machine_hours=8, machine_type="Lathe", shift="Morning")
    res_milling = predictor.predict(quantity=100, machine_hours=8, machine_type="Milling Machine", shift="Morning")

    assert res_lathe["estimated_energy"] != res_milling["estimated_energy"]


def test_unseen_category_rejection():
    """Verify that completely unseen machine type or shift raises a clear error."""
    with pytest.raises(ValueError, match="Unrecognized machine type"):
        predictor.predict(quantity=100, machine_hours=8, machine_type="AlienRayGun", shift="Morning")

    with pytest.raises(ValueError, match="Unrecognized shift"):
        predictor.predict(quantity=100, machine_hours=8, machine_type="CNC", shift="GraveyardWeekendShift")


def test_invalid_numerical_inputs_rejection():
    """Verify rejection of zero or negative quantities and machine hours."""
    with pytest.raises(ValueError, match="Quantity must be a positive number"):
        predictor.predict(quantity=-50, machine_hours=8, machine_type="CNC", shift="Morning")

    with pytest.raises(ValueError, match="Quantity must be a positive number"):
        predictor.predict(quantity=0, machine_hours=8, machine_type="CNC", shift="Morning")

    with pytest.raises(ValueError, match="Machine hours must be a positive number"):
        predictor.predict(quantity=100, machine_hours=0, machine_type="CNC", shift="Morning")


def test_predictor_missing_model_error(tmp_path):
    """Verify that predictor cleanly reports error when artifact is absent."""
    empty_model_path = tmp_path / "nonexistent.joblib"
    custom_predictor = EnergyPredictor(model_path=str(empty_model_path))
    assert not custom_predictor.is_ready()
    assert custom_predictor.load_error is not None
    assert "Model artifact not found" in custom_predictor.load_error

    with pytest.raises(RuntimeError, match="Model artifact not found"):
        custom_predictor.predict(100, 8, "CNC", "Morning")


def test_predictor_metadata_and_version():
    """Verify get_info includes sklearn_version, model_version, and metrics."""
    info = predictor.get_info()
    assert info["is_trained"] is True
    assert "sklearn_version" in info
    assert "model_version" in info
    assert info["error"] is None
