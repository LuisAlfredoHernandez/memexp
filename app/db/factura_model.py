from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone
import uuid
from typing import Optional, TYPE_CHECKING
from enum import Enum

class EstadoFactura(str, Enum):
    PENDIENTE = "PENDIENTE"
    PROCESADA = "PROCESADA"

if TYPE_CHECKING:
    from .orden_venta_model import OrdenVenta

class Factura(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    numero: str = Field(index=True, unique=True)
    orden_venta_id: uuid.UUID = Field(foreign_key="orden_venta.id", unique=True, index=True)
    estado: EstadoFactura = Field(default=EstadoFactura.PENDIENTE)
    subtotal: float = Field(default=0.0)
    impuesto: float = Field(default=0.0)
    total: float = Field(default=0.0)
    notas: Optional[str] = None
    fecha_emision: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_procesamiento: Optional[datetime] = None

    orden_venta: "OrdenVenta" = Relationship(back_populates="factura")
