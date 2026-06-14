from enum import Enum
from pydantic import BaseModel, Field
import uuid
from .operario import MaquinaTipo # Reutilizamos el Enum de tipos

class MaquinaEstado(str, Enum):
    OPERATIVA = "operativa"
    MANTENIMIENTO = "mantenimiento"
    FUERA_SERVICIO = "fuera_servicio"

class MaquinaBase(BaseModel):
    codigo: str = Field(..., min_length=1)
    tipo: MaquinaTipo
    nombre: str = Field(..., min_length=2)
    descripcion: str | None = None
    modelo: str | None = None
    capacidad_por_hora: float = Field(..., ge=0)
    estado: MaquinaEstado
    operario_asignado_id: uuid.UUID | None = None # ID del operario

class Maquina(MaquinaBase):
    id: uuid.UUID

    class ConfigDict:
        from_attributes = True

class MaquinaCreate(MaquinaBase):
    pass

class MaquinaUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1)
    tipo: MaquinaTipo | None = None
    nombre: str | None = Field(default=None, min_length=2)
    descripcion: str | None = None
    modelo: str | None = None
    capacidad_por_hora: float | None = Field(default=None, ge=0)
    estado: MaquinaEstado | None = None
    operario_asignado_id: uuid.UUID | None = None