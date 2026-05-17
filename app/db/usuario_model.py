import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .operario_model import Operario

class Usuario(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nombre: str
    apellido: str
    correo: str = Field(unique=True, index=True)
    rol: str # e.g., 'admin', 'supervisor', 'operario'
    estado: str # e.g., 'activo', 'inactivo'
    hashed_password: str
    operario: Optional["Operario"] = Relationship(back_populates="usuario")
