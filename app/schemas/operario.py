from typing import Literal
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from .usuario import UsuarioBase, UsuarioUpdate, Rol

class MaquinaTipo(str, Enum):
    MERROW = "merrow"
    COVER = "cover"
    PLANA = "plana"
    CORTE = "corte"
    PLANCHA_DTF = "plancha_dtf"

class HabilidadMaquinaria(BaseModel):
    maquina: MaquinaTipo
    nivel_eficiencia: int = Field(default=0, ge=0, le=100)

class OperarioBase(UsuarioBase):
    maquinaActual: MaquinaTipo
    habilidades: list[HabilidadMaquinaria] = Field(default_factory=list)
    orden_actual_id: uuid.UUID | None = Field(default=None, description="ID de la orden en la que el operario está trabajando actualmente")

class OperarioCreate(OperarioBase):
    rol: Literal[Rol.Operario] = Field(
        default=Rol.Operario, 
        description="El rol para este endpoint siempre será Operario y no se puede cambiar."
    )
class Operario(OperarioBase):
    id: uuid.UUID
    
    class ConfigDict:
        from_attributes = True

class OperarioUpdate(UsuarioUpdate):
    rol: None = Field(default=None, description="El rol de un operario no puede ser modificado.")
    habilidades: list[HabilidadMaquinaria] | None = None
    maquinaActual: MaquinaTipo | None = None
    orden_actual_id: uuid.UUID | None = None