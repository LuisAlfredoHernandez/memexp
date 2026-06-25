from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .asignacion_model import AsignacionOrden
    from .operario_model import Operario

class ReporteAvance(SQLModel, table=True):
    __tablename__ = "reporte_avance"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    asignacion_id: uuid.UUID = Field(foreign_key="asignacion_orden.id", index=True)
    operario_id: uuid.UUID = Field(foreign_key="operario.id", index=True)
    
    piezas_reportadas: int = Field(default=0, description="Cantidad de piezas reportadas por el operario")
    piezas_buenas: int = Field(default=0, description="Cantidad de piezas validadas como buenas por el supervisor")
    piezas_defectuosas: int = Field(default=0, description="Cantidad de piezas validadas como defectuosas")
    
    estado: str = Field(default="pendiente", description="Estado del reporte (pendiente, validado, rechazado)")
    fecha_reporte: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fecha_validacion: Optional[datetime] = None
    
    maquina_id: Optional[str] = Field(default=None, description="Máquina/estación en la que se realizó el avance")
    notas: Optional[str] = Field(default=None, description="Notas aclaratorias del operario")

    # Relaciones
    asignacion: Optional["AsignacionOrden"] = Relationship(back_populates="reportes_avance")
    operario: Optional["Operario"] = Relationship(back_populates="reportes_avance")
