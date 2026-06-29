from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timezone

if TYPE_CHECKING:
    from .maquina_model import Maquina
    from .operario_model import Operario

class ReporteAveria(SQLModel, table=True):
    __tablename__ = "reporte_averia"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    maquina_id: uuid.UUID = Field(foreign_key="maquina.id", index=True)
    operario_id: uuid.UUID = Field(foreign_key="operario.id", index=True)
    
    descripcion: str = Field(description="Descripción detallada del fallo o avería")
    tipo_falla: str = Field(description="Tipo de fallo (mecanica, electrica, software, otra)")
    gravedad: str = Field(description="Gravedad del fallo (leve, moderada, critica)")
    detiene_produccion: bool = Field(default=False, description="Indica si la avería detiene la producción")
    
    fecha_reporte: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estado: str = Field(default="pendiente", description="Estado del reporte (pendiente, en_revision, solucionado)")

    # Relaciones
    maquina: Optional["Maquina"] = Relationship()
    operario: Optional["Operario"] = Relationship()
