from sqlmodel import Field, SQLModel, Relationship, JSON, Column
import uuid
from typing import List, TYPE_CHECKING

from app.schemas.operario import MaquinaTipo, HabilidadMaquinaria

if TYPE_CHECKING:
    from .maquina_model import Maquina
    from .usuario_model import Usuario

class Operario(SQLModel, table=True):
    id: uuid.UUID = Field(
        foreign_key="usuario.id",
        primary_key=True,
        index=True
    )
    codigo_empleado: str = Field(unique=True, index=True)
    especialidad: MaquinaTipo
    habilidades: list[HabilidadMaquinaria] = Field(default=[], sa_column=Column(JSON))
    usuario: "Usuario" = Relationship(back_populates="operario")
    maquinas: List["Maquina"] = Relationship(back_populates="operario")
