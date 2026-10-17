from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class EnergyPrediction(Base):
    __tablename__ = "energy_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    production_batch_id = Column(Integer, ForeignKey("production_batches.id", ondelete="SET NULL"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name = Column(String(100), nullable=True)
    quantity = Column(Float, nullable=False)
    machine_hours = Column(Float, nullable=False)
    machine_type_id = Column(Integer, ForeignKey("machine_types.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_type_name = Column(String(100), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    shift_name = Column(String(50), nullable=False)
    estimated_energy_kwh = Column(Float, nullable=False)
    model_version = Column(String(50), nullable=False, default="v1.0.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    production_batch = relationship("ProductionBatch", back_populates="predictions")
    product = relationship("Product", back_populates="predictions")
    machine_type = relationship("MachineType", back_populates="predictions")
    shift = relationship("Shift", back_populates="predictions")
