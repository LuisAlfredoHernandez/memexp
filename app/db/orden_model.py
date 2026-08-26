from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime, timezone
import uuid
from typing import List, Optional, TYPE_CHECKING

from app.schemas.orden import EstadoOrden, TipoOP, Temporada

if TYPE_CHECKING:
    from .linea_orden_model import LineaOrden
    from .asignacion_model import AsignacionOrden
    from .orden_venta_model import OrdenVenta

class Orden(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    numero: str = Field(index=True, unique=True)
    cliente: str
    tipo: TipoOP
    prioridad: str
    temporada: Optional[Temporada] = None
    fecha_entrega_estimada: datetime
    notas: Optional[str] = None
    estado: EstadoOrden = Field(default=EstadoOrden.PENDIENTE)
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    orden_venta_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orden_venta.id", index=True)

    lineas: List["LineaOrden"] = Relationship(back_populates="orden", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    asignaciones: List["AsignacionOrden"] = Relationship(back_populates="orden", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    orden_venta: Optional["OrdenVenta"] = Relationship(back_populates="ordenes_produccion")
