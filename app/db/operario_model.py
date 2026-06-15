from sqlmodel import Field, SQLModel, Relationship, JSON, Column
import uuid
from typing import List, Optional, TYPE_CHECKING

from app.schemas.maquina import MaquinaTipo, HabilidadMaquinaria

if TYPE_CHECKING:
    from .maquina_model import Maquina
    from .usuario_model import Usuario
    from .orden_model import Orden

class Operario(SQLModel, table=True):
    id: uuid.UUID = Field(
        foreign_key="usuario.id",
        primary_key=True,
        index=True
    )
    maquinaActual: MaquinaTipo
    habilidades: list[HabilidadMaquinaria] = Field(default=[], sa_column=Column(JSON))
    
    orden_actual_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orden.id")

    usuario: "Usuario" = Relationship(back_populates="operario")
    maquinas: List["Maquina"] = Relationship(back_populates="operario")

    @property
    def nombre(self) -> str:
        return self.usuario.nombre if self.usuario else ""

    @property
    def apellido(self) -> str:
        return self.usuario.apellido if self.usuario else ""

    @property
    def correo(self) -> str:
        return self.usuario.correo if self.usuario else ""

    @property
    def rol(self) -> str:
        return self.usuario.rol if self.usuario else ""

    @property
    def estado(self) -> str:
        return self.usuario.estado if self.usuario else ""
