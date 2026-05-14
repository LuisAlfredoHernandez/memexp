from pydantic import BaseModel, Field, EmailStr
from enum import str, Enum

class MaquinaTipo(str, Enum):
    MERROW = "merrow"
    COVER = "cover"
    PLANA = "plana"
    CORTE = "corte"
    PLANCHA_DTF = "plancha_dtf"

class HabilidadMaquinaria(BaseModel):
    maquina: MaquinaTipo
    nivel_eficiencia: int = Field(default=0, ge=0, le=100)

class OperarioBase(BaseModel):
    nombre: str = Field(..., min_length=2)
    apellido: str = Field(..., min_length=2)
    correo: EmailStr
    rol: str = "operario"
    estado: str = "inactivo"
    habilidades: list[HabilidadMaquinaria] = []

class OperarioCreate(OperarioBase):
    pass

class Operario(OperarioBase):
    id: str | None = None

    class ConfigDict:
        from_attributes = True