from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone
import uuid
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

class EstadoOrdenVenta(str, Enum):
    EN_ESPERA = "EN_ESPERA"
    EN_PRODUCCION = "EN_PRODUCCION"
    COMPLETADA = "COMPLETADA"
    FACTURADA = "FACTURADA"
    CANCELADA = "CANCELADA"

if TYPE_CHECKING:
    from .linea_orden_venta_model import LineaOrdenVenta
    from .orden_model import Orden
    from .factura_model import Factura

class OrdenVenta(SQLModel, table=True):
    __tablename__ = "orden_venta"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    numero: str = Field(index=True, unique=True)
    cliente: str
    estado: EstadoOrdenVenta = Field(default=EstadoOrdenVenta.EN_ESPERA)
    prioridad: str = Field(default="normal")
    fecha_entrega_estimada: datetime
    notas: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    lineas: List["LineaOrdenVenta"] = Relationship(back_populates="orden_venta", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    ordenes_produccion: List["Orden"] = Relationship(back_populates="orden_venta")
    factura: Optional["Factura"] = Relationship(back_populates="orden_venta", sa_relationship_kwargs={"uselist": False})
