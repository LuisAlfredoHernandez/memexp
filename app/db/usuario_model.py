import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING

from app.schemas.usuario import Rol, UsuarioEstado

if TYPE_CHECKING:
    from .operario_model import Operario

class Usuario(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nombre: str
    apellido: str
    correo: str = Field(unique=True, index=True)
    rol: Rol
    estado: UsuarioEstado
    hashed_password: str
    operario: Optional["Operario"] = Relationship(back_populates="usuario")
