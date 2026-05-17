from pydantic import BaseModel, Field
from enum import Enum
from .usuario import Usuario, UsuarioBase, UsuarioCreate, UsuarioUpdate, Rol

class MaquinaTipo(str, Enum):
    MERROW = "merrow"
    COVER = "cover"
    PLANA = "plana"
    CORTE = "corte"
    PLANCHA_DTF = "plancha_dtf"

class OperarioEstado(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"

class HabilidadMaquinaria(BaseModel):
    maquina: MaquinaTipo
    nivel_eficiencia: int = Field(default=0, ge=0, le=100)


class OperarioBase(UsuarioBase):
    estado: OperarioEstado
    habilidades: list[HabilidadMaquinaria] = Field(default_factory=list)

class OperarioCreate(UsuarioCreate):
    rol: Rol = Field(default=Rol.Operario, frozen=True)
    estado: OperarioEstado = OperarioEstado.INACTIVO
    habilidades: list[HabilidadMaquinaria] = Field(default_factory=list)

class Operario(Usuario):
    estado: OperarioEstado
    habilidades: list[HabilidadMaquinaria] = Field(default_factory=list)

class OperarioUpdate(UsuarioUpdate):
    rol: None = Field(default=None, description="El rol de un operario no puede ser modificado.")
    estado: OperarioEstado | None = None # Override para usar el Enum de Operario
    habilidades: list[HabilidadMaquinaria] | None = None