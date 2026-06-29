from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class AsignacionBase(BaseModel):
    orden_id: uuid.UUID
    operario_id: uuid.UUID
    tarea: str = Field(..., min_length=1)
    piezas_requeridas: int = Field(default=0, ge=0)
    piezas_completadas: int = Field(default=0, ge=0)
    estado: str = Field(default="pendiente")
    notas: str | None = None

class AsignacionCreate(AsignacionBase):
    pass

class AsignacionUpdate(BaseModel):
    tarea: str | None = None
    piezas_requeridas: int | None = Field(default=None, ge=0)
    piezas_completadas: int | None = Field(default=None, ge=0)
    estado: str | None = None
    notas: str | None = None

class AsignacionMiniOrden(BaseModel):
    id: uuid.UUID
    numero: str
    cliente: str

    class ConfigDict:
        from_attributes = True

class AsignacionResponse(AsignacionBase):
    id: uuid.UUID
    fecha_asignacion: datetime
    orden: AsignacionMiniOrden | None = None

    class ConfigDict:
        from_attributes = True
