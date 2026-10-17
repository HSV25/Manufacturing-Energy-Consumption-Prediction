from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from backend.app.database import Base


class MachineType(Base):
    __tablename__ = "machine_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    batches = relationship("ProductionBatch", back_populates="machine_type", passive_deletes=False)
    predictions = relationship("EnergyPrediction", back_populates="machine_type")
