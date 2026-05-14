from pydantic import BaseModel, Field
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
    operario_asignado: str | None = None # ID del operario

class Maquina(MaquinaBase):
    id: str | None = None

    class ConfigDict:
        from_attributes = True

class MaquinaCreate(MaquinaBase):
    pass

class MaquinaUpdate(MaquinaBase):
    pass