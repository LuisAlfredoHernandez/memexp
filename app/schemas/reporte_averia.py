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

class ReporteAveriaProcesar(BaseModel):
    aprobado: bool = Field(..., description="True para aceptar la avería (fuera de servicio), False para rechazar (volver a operativa)")
    notas: str | None = Field(default=None, description="Notas aclaratorias de la decisión")
    nueva_maquina_id: uuid.UUID | None = Field(default=None, description="ID de la nueva máquina para reasignar al operario bloqueado")

class ReporteAveriaResponse(ReporteAveriaBase):
    id: uuid.UUID
    fecha_reporte: datetime
    operario_nombre: str | None = None
    maquina_codigo: str | None = None
    maquina_nombre: str | None = None
    maquina_tipo: str | None = None

    class ConfigDict:
        from_attributes = True
