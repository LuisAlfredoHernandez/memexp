from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ReporteAveriaBase(BaseModel):
    maquina_id: uuid.UUID
    operario_id: uuid.UUID
    descripcion: str = Field(..., min_length=5)
    tipo_falla: str
    gravedad: str
    detiene_produccion: bool = False
    estado: str = "pendiente"

class ReporteAveriaCreate(ReporteAveriaBase):
    pass

class ReporteAveriaUpdate(BaseModel):
    descripcion: str | None = None
    tipo_falla: str | None = None
    gravedad: str | None = None
    detiene_produccion: bool | None = None
    estado: str | None = None

class ReporteAveriaResponse(ReporteAveriaBase):
    id: uuid.UUID
    fecha_reporte: datetime

    class ConfigDict:
        from_attributes = True
