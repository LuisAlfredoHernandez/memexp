from typing import Literal
from pydantic import BaseModel, Field
import uuid
from .usuario import UsuarioBase, UsuarioCreate, UsuarioUpdate, Rol
from .maquina import MaquinaTipo, HabilidadMaquinaria

class OperarioBase(UsuarioBase):
    maquinaActual: MaquinaTipo
    habilidades: list[HabilidadMaquinaria] = Field(default_factory=list)
    orden_actual_id: uuid.UUID | None = Field(default=None, description="ID de la orden en la que el operario está trabajando actualmente")

class OperarioCreate(OperarioBase, UsuarioCreate):
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