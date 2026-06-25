from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import Optional, TYPE_CHECKING, List
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .operario_model import Operario
    from .orden_model import Orden
    from .reporte_avance_model import ReporteAvance

class AsignacionOrden(SQLModel, table=True):
    __tablename__ = "asignacion_orden"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    orden_id: uuid.UUID = Field(foreign_key="orden.id", index=True)
    operario_id: uuid.UUID = Field(foreign_key="operario.id", index=True)
    
    tarea: str = Field(description="Descripción de la tarea asignada (ej: corte, confección, sobrehilado)")
    piezas_requeridas: int = Field(default=0, description="Cantidad de piezas requeridas para esta tarea")
    piezas_completadas: int = Field(default=0, description="Cantidad de piezas completadas")
    estado: str = Field(default="pendiente", description="Estado de la asignación (pendiente, en_proceso, completada)")
    
    fecha_asignacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notas: Optional[str] = None

    # Relaciones
    orden: Optional["Orden"] = Relationship(back_populates="asignaciones")
    operario: Optional["Operario"] = Relationship(back_populates="asignaciones")
    reportes_avance: List["ReporteAvance"] = Relationship(back_populates="asignacion", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

