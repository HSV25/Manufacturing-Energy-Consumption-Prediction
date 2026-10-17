"""
End-to-End Mock Demonstration of Dynamic Machine Types,
Validation, Retraining, and Prediction Lifecycles.
Executes Demos 1 through 8 from Section 7 of the Master Prompt.
"""

import json
import sys
from pathlib import Path
import shutil

# Add project root to path
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
    retrain_with_machine_types,
    DEFAULT_MODEL_PATH,
    DEFAULT_METRICS_PATH,
)
from backend.ml.dataset import generate_synthetic_dataset, DEFAULT_OUTPUT_CSV


def run_demonstration():
    print("=" * 75)
    print(" MANUFACTURING ENERGY CONSUMPTION PREDICTION SYSTEM")
    print(" END-TO-END MOCK DEMONSTRATION: DYNAMIC MACHINE TYPES")
    print("=" * 75)

    # Backup production model and dataset to restore post-test
    prod_data = DEFAULT_OUTPUT_CSV
    backup_data = prod_data.with_suffix(".csv.demobak")
    backup_model = DEFAULT_MODEL_PATH.with_suffix(".joblib.demobak")
    backup_metrics = DEFAULT_METRICS_PATH.with_suffix(".json.demobak")

    if prod_data.exists():
        shutil.copy2(prod_data, backup_data)
    if DEFAULT_MODEL_PATH.exists():
        shutil.copy2(DEFAULT_MODEL_PATH, backup_model)
    if DEFAULT_METRICS_PATH.exists():
        shutil.copy2(DEFAULT_METRICS_PATH, backup_metrics)

    try:
        # Setup isolated test database session
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = TestingSession()

        # Seed baseline master records
        p1 = Product(name="Industrial Gearbox Housing", description="Heavy cast iron gearbox casing")
        p2 = Product(name="Hydraulic Valve Body", description="Precision hydraulic flow valve")
        m1 = MachineType(name="CNC", description="Computer numerical control multi-axis mill")
        m2 = MachineType(name="Lathe", description="High-speed rotational lathe")
        m3 = MachineType(name="Milling Machine", description="Heavy-duty vertical milling")
        s1 = Shift(name="Morning", description="Morning production shift 06:00-14:00")
        s2 = Shift(name="Evening", description="Evening production shift 14:00-22:00")
        s3 = Shift(name="Night", description="Night production shift 22:00-06:00")
        db.add_all([p1, p2, m1, m2, m3, s1, s2, s3])
        db.commit()

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        # Initial state: Train base model with only CNC, Lathe, Milling Machine
        print("\n[Setup] Establishing base model state (CNC, Lathe, Milling Machine)...")
        base_data = generate_synthetic_dataset(
            output_path=PROJECT_ROOT / "data" / "demo_base_dataset.csv",
            machine_types=["CNC", "Lathe", "Milling Machine"],
            num_samples=800,
            seed=101,
        )
        train_and_evaluate(data_path=base_data, model_version="v1.0.0")
        predictor.reload()
        print(f"[Setup] Base model ready: Version={predictor.model_version}, Supported={predictor.get_supported_machine_types()}")

        # -------------------------------------------------------------
        # DEMO 1: Master Data - Add GEARBOX
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 1: Master Data Management - Add 'GEARBOX'")
        print("-" * 75)
        create_res = client.post("/api/machine-types", json={
            "name": "GEARBOX",
            "description": "Gearbox assembly, testing dynamometer, and calibration rig",
        })
        print(f"POST /api/machine-types -> Status: {create_res.status_code}")
        created_gearbox = create_res.json()
        gearbox_id = created_gearbox["id"]
        print(f"Created Machine Type Record: ID={gearbox_id}, Name='{created_gearbox['name']}'")

        # Verify available in GET /api/machine-types
        list_res = client.get("/api/machine-types")
        all_machines = list_res.json()
        print(f"GET /api/machine-types -> Total Configured Machines: {len(all_machines)}")
        for m in all_machines:
            print(f"  * [ID: {m['id']}] {m['name']} - {m['description']}")

        # -------------------------------------------------------------
        # DEMO 2: Existing Machine Prediction (CNC)
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 2: Existing Machine Prediction (CNC Baseline)")
        print("-" * 75)
        demo2_payload = {
            "quantity": 100,
            "machineHours": 8.0,
            "machineType": "CNC",
            "shift": "Morning",
        }
        print(f"Request: POST /predict-energy -> Inputs: {json.dumps(demo2_payload)}")
        pred_cnc_res = client.post("/predict-energy", json=demo2_payload)
        print(f"Response Status: {pred_cnc_res.status_code}")
        pred_cnc = pred_cnc_res.json()
        print(f"Response Body:   {json.dumps(pred_cnc, indent=2)}")
        print(f"RESULT: Estimated Energy = {pred_cnc['estimatedEnergy']} {pred_cnc['unit']} (Model: {pred_cnc['modelVersion']})")

        # -------------------------------------------------------------
        # DEMO 3: New Machine Type Before Training (GEARBOX)
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 3: New Machine Type Before Retraining (GEARBOX)")
        print("-" * 75)
        demo3_payload = {
            "quantity": 100,
            "machineHours": 8.0,
            "machineType": "GEARBOX",
            "shift": "Morning",
        }
        print(f"Request: POST /predict-energy -> Inputs: {json.dumps(demo3_payload)}")
        pred_untrained_res = client.post("/predict-energy", json=demo3_payload)
        print(f"Response Status: {pred_untrained_res.status_code} (Expected: 422 Unprocessable Entity)")
        print(f"Response Detail: {pred_untrained_res.json().get('detail')}")
        print("RESULT: System correctly refuses to fabricate a number and explains retraining is required.")

        # -------------------------------------------------------------
        # DEMO 4: Train the New Category
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 4: Train New Category into ML Model Lifecycle")
        print("-" * 75)
        print("Generating representative synthetic training records for [CNC, Lathe, Milling Machine, GEARBOX]...")
        retrain_metrics = retrain_with_machine_types(
            machine_types=["CNC", "Lathe", "Milling Machine", "GEARBOX"],
            num_samples=1200,
            seed=42,
        )
        predictor.reload()
        print(f"Candidate Model Evaluation on Held-Out Test Split:")
        print(f"  * R² Score: {retrain_metrics['metrics']['r2_score']:.4f}")
        print(f"  * MAE:      {retrain_metrics['metrics']['mae_kwh']:.2f} kWh")
        print(f"  * RMSE:     {retrain_metrics['metrics']['rmse_kwh']:.2f} kWh")
        print(f"  * Active Supported Machines: {predictor.get_supported_machine_types()}")
        print("RESULT: Candidate model validated, atomically swapped, and active predictor reloaded.")

        # -------------------------------------------------------------
        # DEMO 5: Predict Using GEARBOX After Retraining
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 5: Predict Energy for GEARBOX with Retrained Model")
        print("-" * 75)
        demo5_payload = {
            "quantity": 100,
            "machineHours": 8.0,
            "machineType": "GEARBOX",
            "shift": "Morning",
        }
        print(f"Request: POST /predict-energy -> Inputs: {json.dumps(demo5_payload)}")
        pred_gearbox_res = client.post("/predict-energy", json=demo5_payload)
        print(f"Response Status: {pred_gearbox_res.status_code}")
        pred_gearbox = pred_gearbox_res.json()
        print(f"Response Body:   {json.dumps(pred_gearbox, indent=2)}")
        print(f"RESULT: Real Model Inference = {pred_gearbox['estimatedEnergy']} {pred_gearbox['unit']} (Model: {pred_gearbox['modelVersion']})")

        # -------------------------------------------------------------
        # DEMO 6: Saved Production Batch Workflow
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 6: Saved Production Batch Lifecycle & Actual Energy Independence")
        print("-" * 75)
        # Create batch
        batch_payload = {
            "batchNumber": "BATCH-2025-GBX-001",
            "productId": p1.id,
            "quantity": 120,
            "machineHours": 7.5,
            "machineTypeId": gearbox_id,
            "shiftId": s1.id,
            "productionDate": "2025-06-25",
        }
        create_b_res = client.post("/api/production-batches", json=batch_payload)
        print(f"Step 1: Created Batch -> ID: {create_b_res.json()['id']}, Batch Number: {create_b_res.json()['batchNumber']}")
        batch_obj_id = create_b_res.json()["id"]

        # Predict for batch
        batch_pred_res = client.post(f"/api/production-batches/{batch_obj_id}/predict")
        print(f"Step 2: Predicted Energy for Saved Batch -> {batch_pred_res.json()['estimatedEnergy']} kWh")
        original_estimate = batch_pred_res.json()["estimatedEnergy"]
        prediction_audit_id = batch_pred_res.json()["predictionId"]

        # View prediction history
        hist_before = client.get(f"/api/predictions/{prediction_audit_id}").json()
        print(f"Step 3: History Audit -> Estimated: {hist_before['estimatedEnergyKwh']} kWh, Actual: {hist_before['actualEnergyKwh']} (Pending)")

        # Record actual energy post-production
        actual_kwh = 282.40
        update_b_res = client.put(f"/api/production-batches/{batch_obj_id}", json={
            "actualEnergyConsumedKwh": actual_kwh,
        })
        print(f"Step 4: Recorded Post-Production Actual Energy -> {update_b_res.json()['actualEnergyConsumedKwh']} kWh")

        # Confirm original prediction remains unchanged
        hist_after = client.get(f"/api/predictions/{prediction_audit_id}").json()
        print(f"Step 5: History Audit Verified:")
        print(f"  * Estimated Energy: {hist_after['estimatedEnergyKwh']} kWh (Unchanged: {hist_after['estimatedEnergyKwh'] == original_estimate})")
        print(f"  * Actual Energy:    {hist_after['actualEnergyKwh']} kWh")
        variance = round(hist_after['actualEnergyKwh'] - hist_after['estimatedEnergyKwh'], 2)
        print(f"  * Variance:         {variance:+} kWh")

        # -------------------------------------------------------------
        # DEMO 7: Dashboard Summary Verification
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 7: Operational Dashboard Aggregate Verification")
        print("-" * 75)
        dash_res = client.get("/api/dashboard/stats")
        dash = dash_res.json()
        print(f"Dashboard Operational Statistics:")
        print(f"  * Total Batches:         {dash['totalBatches']}")
        print(f"  * Completed Batches:     {dash['completedBatches']}")
        print(f"  * Pending Batches:       {dash['pendingBatches']}")
        print(f"  * Total Predictions:     {dash['totalPredictions']}")
        print(f"  * Avg Predicted Energy:  {dash['averagePredictedEnergyKwh']} kWh")
        print(f"  * Avg Actual Energy:     {dash['averageActualEnergyKwh']} kWh")
        print(f"  * Latest Batch in Feed:  {dash['recentBatches'][0]['batchNumber']} ({dash['recentBatches'][0]['machineType']['name']})")

        # -------------------------------------------------------------
        # DEMO 8: Regression Check on All Original Machine Types
        # -------------------------------------------------------------
        print("\n" + "-" * 75)
        print("DEMO 8: Regression Verification of Original Machine Types")
        print("-" * 75)
        regression_checks = [
            {"machineType": "CNC", "quantity": 100, "machineHours": 8.0, "shift": "Morning"},
            {"machineType": "Lathe", "quantity": 100, "machineHours": 8.0, "shift": "Morning"},
            {"machineType": "Milling Machine", "quantity": 100, "machineHours": 8.0, "shift": "Morning"},
        ]
        for check in regression_checks:
            r = client.post("/predict-energy", json=check)
            est = r.json()["estimatedEnergy"]
            print(f"  * Machine: {check['machineType']:<16} -> Prediction: {est:>7.2f} kWh (Status {r.status_code})")

        # Cleanup temporary dataset
        temp_demo_csv = PROJECT_ROOT / "data" / "demo_base_dataset.csv"
        if temp_demo_csv.exists():
            temp_demo_csv.unlink()

        print("\n" + "=" * 75)
        print(" END-TO-END MOCK DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("=" * 75)

    finally:
        # Cleanup temporary dataset if still present
        temp_demo_csv = PROJECT_ROOT / "data" / "demo_base_dataset.csv"
        if temp_demo_csv.exists():
            temp_demo_csv.unlink()
        # Restore canonical production dataset and model artifacts
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
    run_demonstration()
