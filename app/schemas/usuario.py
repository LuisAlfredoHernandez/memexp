from enum import Enum
from pydantic import BaseModel, EmailStr, Field
import uuid

class Rol(str, Enum):
    Operario = "operario"
    Supervisor = "supervisor"
    Administrador = "administrador"

class UsuarioEstado(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"

class UsuarioBase(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    rol: Rol
    estado: UsuarioEstado

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8)
    estado: UsuarioEstado = UsuarioEstado.INACTIVO
    
class Usuario(UsuarioBase):
    id: uuid.UUID

    class ConfigDict:
        from_attributes = True

class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    correo: EmailStr | None = None
    rol: Rol | None = None
    estado: UsuarioEstado | None = None
    password: str | None = None