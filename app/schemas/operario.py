from typing import Literal
from pydantic import BaseModel, Field, field_validator
import uuid
from .usuario import UsuarioBase, UsuarioCreate, UsuarioUpdate, Rol
from .maquina import MaquinaTipo, HabilidadMaquinaria

class OperarioBase(UsuarioBase):
    maquina_actual_id: uuid.UUID | None = Field(default=None, description="ID de la máquina física asignada")
    habilidades: list[HabilidadMaquinaria] = Field(default_factory=list)

    @field_validator('habilidades')
    @classmethod
    def check_unique_habilidades(cls, v: list[HabilidadMaquinaria]) -> list[HabilidadMaquinaria]:
        v_maquinas = [h.maquina for h in v]
        if len(v_maquinas) != len(set(v_maquinas)):
            raise ValueError("No puede haber habilidades duplicadas para el mismo tipo de máquina.")
        return v
    
    orden_actual_id: uuid.UUID | None = Field(default=None, description="ID de la orden en la que el operario está trabajando actualmente")

class OperarioCreate(OperarioBase, UsuarioCreate):
    rol: Literal[Rol.Operario] = Field(
        default=Rol.Operario, 
        description="El rol para este endpoint siempre será Operario y no se puede cambiar."
    )
class Operario(OperarioBase):
    id: uuid.UUID
    piezas_buenas: int = 0
    piezas_defectuosas: int = 0
    
    class ConfigDict:
        from_attributes = True

class OperarioUpdate(UsuarioUpdate):
    rol: None = Field(default=None, description="El rol de un operario no puede ser modificado.")
    habilidades: list[HabilidadMaquinaria] | None = None
    maquina_actual_id: uuid.UUID | None = None
    orden_actual_id: uuid.UUID | None = None