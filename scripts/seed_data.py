import logging
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import random

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database import SessionLocal, Base, engine
from backend.app.models.product import Product
from backend.app.models.machine_type import MachineType
from backend.app.models.shift import Shift
from backend.app.models.production_batch import ProductionBatch
from backend.app.models.energy_prediction import EnergyPrediction
from backend.ml.predict import predictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

INITIAL_PRODUCTS = [
    {"name": "Industrial Gearbox Housing", "description": "Cast iron heavy gearbox housing for wind turbines"},
    {"name": "Hydraulic Valve Body", "description": "High-pressure aluminum manifold block"},
    {"name": "Turbine Blade Mount", "description": "Titanium alloy precision turbine blade mounting collar"},
    {"name": "Precision Drive Shaft", "description": "Heat-treated carbon steel automotive drive shaft"},
    {"name": "Flange Connector", "description": "Stainless steel high-pressure pipe connection flange"},
]

INITIAL_MACHINE_TYPES = [
    {"name": "CNC", "description": "Computer Numerical Control multi-axis machining center"},
    {"name": "Lathe", "description": "Heavy-duty rotational turning machine"},
    {"name": "Milling Machine", "description": "Vertical and horizontal mechanical milling station"},
    {"name": "GEARBOX", "description": "Heavy-duty industrial gearbox assembly and testing cell"},
]

INITIAL_SHIFTS = [
    {"name": "Morning", "description": "06:00 AM – 02:00 PM (06:00 – 14:00) Morning First Shift"},
    {"name": "Afternoon", "description": "12:00 PM – 04:00 PM (12:00 – 16:00) Afternoon Production Shift"},
    {"name": "Evening", "description": "02:00 PM – 10:00 PM (14:00 – 22:00) Evening Second Shift"},
    {"name": "Night", "description": "10:00 PM – 06:00 AM (22:00 – 06:00) Overnight Third Shift"},
]


def seed_database():
    """Seeds the SQLite database with master data and sample production batches."""
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Seed Products
        logger.info("Seeding Products...")
        product_map = {}
        for p_data in INITIAL_PRODUCTS:
            prod = db.query(Product).filter(Product.name == p_data["name"]).first()
            if not prod:
                prod = Product(name=p_data["name"], description=p_data["description"])
                db.add(prod)
                db.flush()
                logger.info(f"Created Product: {prod.name}")
            product_map[prod.name] = prod

        # 2. Seed Machine Types
        logger.info("Seeding Machine Types...")
        machine_map = {}
        for m_data in INITIAL_MACHINE_TYPES:
            mt = db.query(MachineType).filter(MachineType.name == m_data["name"]).first()
            if not mt:
                mt = MachineType(name=m_data["name"], description=m_data["description"])
                db.add(mt)
                db.flush()
                logger.info(f"Created Machine Type: {mt.name}")
            machine_map[mt.name] = mt

        # 3. Seed Shifts
        logger.info("Seeding Shifts...")
        shift_map = {}
        for s_data in INITIAL_SHIFTS:
            sh = db.query(Shift).filter(Shift.name == s_data["name"]).first()
            if not sh:
                sh = Shift(name=s_data["name"], description=s_data["description"])
                db.add(sh)
                db.flush()
                logger.info(f"Created Shift: {sh.name}")
            shift_map[sh.name] = sh

        db.commit()

        # 4. Seed Initial Batches if none exist
        existing_batch_count = db.query(ProductionBatch).count()
        if existing_batch_count == 0:
            logger.info("Seeding initial sample production batches...")
            products_list = list(product_map.values())
            machines_list = list(machine_map.values())
            shifts_list = list(shift_map.values())

            today = date.today()

            sample_batch_configs = [
                # Completed batches (with actual energy)
                {"days_ago": 10, "q": 120, "h": 7.5, "m": "CNC", "s": "Morning", "actual": 272.4},
                {"days_ago": 9, "q": 80, "h": 5.0, "m": "Lathe", "s": "Evening", "actual": 145.8},
                {"days_ago": 8, "q": 150, "h": 9.0, "m": "Milling Machine", "s": "Morning", "actual": 485.2},
                {"days_ago": 7, "q": 200, "h": 12.0, "m": "CNC", "s": "Night", "actual": 498.0},
                {"days_ago": 6, "q": 90, "h": 6.0, "m": "Lathe", "s": "Morning", "actual": 168.3},
                {"days_ago": 5, "q": 110, "h": 7.0, "m": "Milling Machine", "s": "Evening", "actual": 382.1},
                {"days_ago": 4, "q": 250, "h": 14.0, "m": "CNC", "s": "Morning", "actual": 595.6},
                # Pending batches (planned, actual energy None)
                {"days_ago": 2, "q": 130, "h": 8.0, "m": "CNC", "s": "Morning", "actual": None},
                {"days_ago": 1, "q": 95, "h": 5.5, "m": "Lathe", "s": "Evening", "actual": None},
                {"days_ago": 0, "q": 180, "h": 10.5, "m": "Milling Machine", "s": "Night", "actual": None},
            ]

            for idx, cfg in enumerate(sample_batch_configs, start=1):
                p_obj = products_list[(idx - 1) % len(products_list)]
                m_obj = machine_map[cfg["m"]]
                s_obj = shift_map[cfg["s"]]

                batch = ProductionBatch(
                    batch_number=f"DEMO-2025-{idx:03d}",
                    product_id=p_obj.id,
                    quantity=cfg["q"],
                    machine_hours=cfg["h"],
                    machine_type_id=m_obj.id,
                    shift_id=s_obj.id,
                    production_date=today - timedelta(days=cfg["days_ago"]),
                    actual_energy_consumed_kwh=cfg["actual"],
                )
                db.add(batch)
                db.flush()

                # Generate a prediction audit record for demonstration
                if predictor.is_ready():
                    pred_res = predictor.predict(
                        quantity=cfg["q"],
                        machine_hours=cfg["h"],
                        machine_type=m_obj.name,
                        shift=s_obj.name,
                    )
                    prediction_rec = EnergyPrediction(
                        production_batch_id=batch.id,
                        product_id=p_obj.id,
                        product_name=p_obj.name,
                        quantity=cfg["q"],
                        machine_hours=cfg["h"],
                        machine_type_id=m_obj.id,
                        machine_type_name=m_obj.name,
                        shift_id=s_obj.id,
                        shift_name=s_obj.name,
                        estimated_energy_kwh=pred_res["estimated_energy"],
                        model_version=pred_res["model_version"],
                    )
                    db.add(prediction_rec)

            db.commit()
            logger.info("Successfully seeded sample batches and predictions.")
        else:
            logger.info(f"Database already contains {existing_batch_count} batches. Skipping batch seeding.")

        logger.info("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
