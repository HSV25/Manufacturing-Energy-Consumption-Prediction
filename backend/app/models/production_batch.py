from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ProductionBatch(Base):
    __tablename__ = "production_batches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    batch_number = Column(String(50), unique=True, nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    machine_hours = Column(Float, nullable=False)
    machine_type_id = Column(Integer, ForeignKey("machine_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="RESTRICT"), nullable=False, index=True)
    production_date = Column(Date, nullable=False, index=True)
    actual_energy_consumed_kwh = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    product = relationship("Product", back_populates="batches")
    machine_type = relationship("MachineType", back_populates="batches")
    shift = relationship("Shift", back_populates="batches")
    predictions = relationship("EnergyPrediction", back_populates="production_batch")
