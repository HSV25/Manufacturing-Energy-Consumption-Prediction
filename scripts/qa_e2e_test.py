"""
Comprehensive End-to-End QA Validation Script.
Executes the exact 12-step End-to-End QA workflow specified in Section 6 of the
Final QA Prompt against an isolated test environment.
"""

import json
import sys
from pathlib import Path
import shutil

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift
from backend.ml.predict import predictor
from backend.ml.train_model import (
    train_and_evaluate,
    DEFAULT_MODEL_PATH,
    DEFAULT_METRICS_PATH,
)
from backend.ml.dataset import generate_synthetic_dataset, DEFAULT_OUTPUT_CSV


def run_qa_e2e_suite():
    print("=" * 80)
    print(" QA VERIFICATION: COMPLETE 12-STEP WORKFLOW (SECTION 6)")
    print("=" * 80)

    # Backup production model and dataset to restore post-test
    prod_data = DEFAULT_OUTPUT_CSV
    backup_data = prod_data.with_suffix(".csv.qabak")
    backup_model = DEFAULT_MODEL_PATH.with_suffix(".joblib.qabak")
    backup_metrics = DEFAULT_METRICS_PATH.with_suffix(".json.qabak")

    if prod_data.exists():
        shutil.copy2(prod_data, backup_data)
    if DEFAULT_MODEL_PATH.exists():
        shutil.copy2(DEFAULT_MODEL_PATH, backup_model)
    if DEFAULT_METRICS_PATH.exists():
        shutil.copy2(DEFAULT_METRICS_PATH, backup_metrics)

    try:
        # Isolated test database
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestingSession()

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        # Setup base model state
        base_data = generate_synthetic_dataset(
            output_path=PROJECT_ROOT / "data" / "qa_base_dataset.csv",
            machine_types=["CNC", "Lathe", "Milling Machine"],
            num_samples=400,
            seed=2026,
        )
        train_and_evaluate(data_path=base_data, model_version="v1.0.0")
        predictor.reload()
        print(f"[Setup] Base model loaded: {predictor.model_version}, Machines: {predictor.get_supported_machine_types()}")

        # -------------------------------------------------------------
        # Step 1: Create a product, machine type, and shift
        # -------------------------------------------------------------
        print("\n--- Step 1: Create a product, machine type, and shift ---")
        p_res = client.post("/api/products", json={"name": "QA Hydraulic Valve", "description": "High pressure valve"})
        assert p_res.status_code == 201
        prod = p_res.json()
        print(f"Product Created:      ID={prod['id']}, Name='{prod['name']}'")

        m_res = client.post("/api/machine-types", json={"name": "CNC", "description": "CNC 5-Axis Milling Center"})
        assert m_res.status_code == 201
        machine = m_res.json()
        print(f"Machine Type Created: ID={machine['id']}, Name='{machine['name']}'")

        s_res = client.post("/api/shifts", json={"name": "Morning", "description": "06:00 to 14:00 First Shift"})
        assert s_res.status_code == 201
        shift = s_res.json()
        print(f"Shift Created:        ID={shift['id']}, Name='{shift['name']}'")

        # -------------------------------------------------------------
        # Step 2: Create a production batch with actual energy consumption
        # -------------------------------------------------------------
        print("\n--- Step 2: Create a production batch with actual energy ---")
        batch_payload = {
            "batchNumber": "BATCH-QA-2026-001",
            "productId": prod["id"],
            "quantity": 150,
            "machineHours": 8.0,
            "machineTypeId": machine["id"],
            "shiftId": shift["id"],
            "productionDate": "2026-10-15",
            "actualEnergyConsumedKwh": 375.40,
        }
        b_res = client.post("/api/production-batches", json=batch_payload)
        assert b_res.status_code == 201
        batch = b_res.json()
        print(f"Batch Created: ID={batch['id']}, Number='{batch['batchNumber']}', Actual Energy={batch['actualEnergyConsumedKwh']} kWh")

        # -------------------------------------------------------------
        # Step 3: Request an energy prediction (Workflow B)
        # -------------------------------------------------------------
        print("\n--- Step 3: Request an energy prediction for the batch ---")
        pred_res = client.post(f"/api/production-batches/{batch['id']}/predict")
        assert pred_res.status_code == 200
        pred = pred_res.json()
        pred_id = pred["predictionId"]
        estimated_kwh = pred["estimatedEnergy"]
        print(f"Prediction Generated: PredictionID={pred_id}, Estimated Energy={estimated_kwh} {pred['unit']}")

        # -------------------------------------------------------------
        # Step 4: Verify that the prediction is stored in history
        # -------------------------------------------------------------
        print("\n--- Step 4: Verify prediction is stored in history ---")
        h_res = client.get(f"/api/predictions/{pred_id}")
        assert h_res.status_code == 200
        history_record = h_res.json()
        print(f"History Audit Record: ID={history_record['id']}, Batch='{history_record['batchNumber']}'")
        assert history_record["estimatedEnergyKwh"] == estimated_kwh
        print(f"Estimated Energy Verified: {history_record['estimatedEnergyKwh']} kWh")

        # -------------------------------------------------------------
        # Step 5: Compare estimated energy with actual energy
        # -------------------------------------------------------------
        print("\n--- Step 5: Compare estimated energy with actual energy ---")
        print(f"Stored Estimated Energy: {history_record['estimatedEnergyKwh']} kWh")
        print(f"Stored Actual Energy:    {history_record['actualEnergyKwh']} kWh")
        variance = round(history_record['actualEnergyKwh'] - history_record['estimatedEnergyKwh'], 2)
        print(f"Calculated Variance:     {variance:+} kWh")
        assert history_record["estimatedEnergyKwh"] != history_record["actualEnergyKwh"]

        # -------------------------------------------------------------
        # Step 6: Verify that neither value overwrites the other
        # -------------------------------------------------------------
        print("\n--- Step 6: Verify neither value overwrites the other ---")
        assert history_record["estimatedEnergyKwh"] == estimated_kwh
        assert history_record["actualEnergyKwh"] == 375.40
        print("[OK] Verification confirmed: Prediction audit and actual batch consumption remain completely independent!")

        # -------------------------------------------------------------
        # Step 7: Register a new machine type that current model does not support
        # -------------------------------------------------------------
        print("\n--- Step 7: Register a new machine type that current model does not support ---")
        unsupported_res = client.post("/api/machine-types", json={
            "name": "QA_LASER_WELDING",
            "description": "Robotic fiber laser welding cell",
        })
        assert unsupported_res.status_code == 201
        unsupported_m = unsupported_res.json()
        print(f"New Machine Registered in SQLite: ID={unsupported_m['id']}, Name='{unsupported_m['name']}'")

        # -------------------------------------------------------------
        # Step 8: Confirm system explains the retraining requirement
        # -------------------------------------------------------------
        print("\n--- Step 8: Confirm system explains retraining requirement ---")
        # A. Check model status endpoint
        status_res = client.get("/api/dashboard/model-status")
        assert status_res.status_code == 200
        model_st = status_res.json()
        print(f"Model Status: Retraining Required = {model_st['retraining_required']}")
        print(f"Unsupported Configured Machines: {model_st['unsupported_configured_machines']}")
        assert model_st["retraining_required"] is True
        assert "QA_LASER_WELDING" in model_st["unsupported_configured_machines"]

        # B. Attempt prediction with unsupported machine
        unsupported_pred_res = client.post("/predict-energy", json={
            "quantity": 100,
            "machineHours": 8.0,
            "machineType": "QA_LASER_WELDING",
            "shift": "Morning",
        })
        assert unsupported_pred_res.status_code == 422
        err_msg = unsupported_pred_res.json()["detail"]
        print(f"API Error Response (HTTP 422): '{err_msg}'")
        assert "not been trained for this category" in err_msg
        assert "retrain" in err_msg.lower()

        # -------------------------------------------------------------
        # Step 9: Retrain model using the existing supported training workflow
        # -------------------------------------------------------------
        print("\n--- Step 9: Retrain model using supported workflow ---")
        retrain_res = client.post("/api/dashboard/retrain-model")
        assert retrain_res.status_code == 200
        retrain_data = retrain_res.json()
        print(f"Retraining Success: {retrain_data['message']}")
        print(f"Updated Supported Machines: {retrain_data['supported_machine_types']}")
        assert "QA_LASER_WELDING" in retrain_data["supported_machine_types"]

        # -------------------------------------------------------------
        # Step 10: Confirm newly supported machine can be predicted after retraining
        # -------------------------------------------------------------
        print("\n--- Step 10: Confirm newly supported machine can be predicted ---")
        success_pred_res = client.post("/predict-energy", json={
            "quantity": 100,
            "machineHours": 8.0,
            "machineType": "QA_LASER_WELDING",
            "shift": "Morning",
        })
        assert success_pred_res.status_code == 200
        new_pred = success_pred_res.json()
        print(f"Prediction for QA_LASER_WELDING: {new_pred['estimatedEnergy']} {new_pred['unit']} (Model: {new_pred['modelVersion']})")
        assert new_pred["estimatedEnergy"] > 0

        # -------------------------------------------------------------
        # Step 11: Simulate retraining failure and confirm active model remains usable
        # -------------------------------------------------------------
        print("\n--- Step 11: Simulate retraining failure and confirm active model remains usable ---")
        current_mtime = DEFAULT_MODEL_PATH.stat().st_mtime_ns
        current_model_version = predictor.model_version

        # Attempt training with corrupt dataset (insufficient rows & invalid target)
        corrupt_csv = PROJECT_ROOT / "data" / "corrupt_data.csv"
        with open(corrupt_csv, "w", encoding="utf-8") as f:
            f.write("quantity,machine_hours,machine_type,shift,actual_energy_consumed_kwh\n")
            f.write("10,2,CNC,Morning,0\n")

        try:
            train_and_evaluate(data_path=corrupt_csv)
            print("[FAIL] Training on corrupt data unexpectedly succeeded.")
            assert False
        except Exception as e:
            print(f"Simulated Retraining Failure Caught: {e}")

        if corrupt_csv.exists():
            corrupt_csv.unlink()

        # Verify active model remains intact and usable
        assert DEFAULT_MODEL_PATH.exists()
        assert DEFAULT_MODEL_PATH.stat().st_mtime_ns == current_mtime
        predictor.reload()
        assert predictor.is_ready()
        assert predictor.model_version == current_model_version

        # Verify predictions continue working seamlessly on active model
        test_recheck = client.post("/predict-energy", json={
            "quantity": 100,
            "machineHours": 8.0,
            "machineType": "CNC",
            "shift": "Morning",
        })
        assert test_recheck.status_code == 200
        print(f"Active Model Resilience Check: {test_recheck.json()['estimatedEnergy']} kWh (Status: {test_recheck.status_code})")
        print("[OK] Active model remains 100% usable after simulated retraining failure!")

        # -------------------------------------------------------------
        # Step 12: Verify dashboard totals and averages against isolated database
        # -------------------------------------------------------------
        print("\n--- Step 12: Verify dashboard totals and averages against isolated database ---")
        dash_res = client.get("/api/dashboard/stats")
        assert dash_res.status_code == 200
        stats = dash_res.json()
        print(f"Dashboard Stats:")
        print(f"  * Total Products:      {stats['totalProducts']} (Expected: 1)")
        print(f"  * Total Machine Types: {stats['totalMachineTypes']} (Expected: 2: CNC, QA_LASER_WELDING)")
        print(f"  * Total Shifts:        {stats['totalShifts']} (Expected: 1: Morning)")
        print(f"  * Total Batches:       {stats['totalBatches']} (Expected: 1)")
        print(f"  * Completed Batches:   {stats['completedBatches']} (Expected: 1)")
        print(f"  * Total Predictions:   {stats['totalPredictions']} (Expected: 3)")
        print(f"  * Avg Actual Energy:   {stats['averageActualEnergyKwh']} kWh (Expected: 375.40)")
        assert stats["totalProducts"] == 1
        assert stats["totalMachineTypes"] == 2
        assert stats["totalShifts"] == 1
        assert stats["totalBatches"] == 1
        assert stats["completedBatches"] == 1
        assert stats["totalPredictions"] == 3
        assert stats["averageActualEnergyKwh"] == 375.40
        print("[OK] Dashboard statistics match isolated database state exactly!")

        # Cleanup temporary dataset
        if (PROJECT_ROOT / "data" / "qa_base_dataset.csv").exists():
            (PROJECT_ROOT / "data" / "qa_base_dataset.csv").unlink()

        print("\n" + "=" * 80)
        print(" ALL 12 WORKFLOW STEPS PASSED WITH 100% SUCCESS")
        print("=" * 80)

    finally:
        # Restore production dataset and model artifacts
        if backup_data.exists():
            shutil.copy2(backup_data, prod_data)
            backup_data.unlink()
        if backup_model.exists():
            shutil.copy2(backup_model, DEFAULT_MODEL_PATH)
            backup_model.unlink()
        if backup_metrics.exists():
            shutil.copy2(backup_metrics, DEFAULT_METRICS_PATH)
            backup_metrics.unlink()
        predictor.reload()


if __name__ == "__main__":
    run_qa_e2e_suite()
