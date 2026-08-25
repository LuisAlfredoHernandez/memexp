from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone
import uuid
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

class EstadoOrdenCompra(str, Enum):
    PENDIENTE = "PENDIENTE"
    RECIBIDA = "RECIBIDA"
    CANCELADA = "CANCELADA"

if TYPE_CHECKING:
    from .linea_orden_compra_model import LineaOrdenCompra

class OrdenCompra(SQLModel, table=True):
    __tablename__ = "orden_compra"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    numero: str = Field(index=True, unique=True)
    proveedor: str
    estado: EstadoOrdenCompra = Field(default=EstadoOrdenCompra.PENDIENTE)
    notas: Optional[str] = None
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    lineas: List["LineaOrdenCompra"] = Relationship(back_populates="orden_compra", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
