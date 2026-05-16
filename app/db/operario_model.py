from app.schemas.maquina import Maquina
from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import List

# Se asume que estos enums existen en el esquema de operario
from app.schemas.operario import MaquinaTipo, OperarioEstado 

class Operario(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nombre: str
    apellido: str
    codigo_empleado: str = Field(unique=True, index=True)
    especialidad: MaquinaTipo
    estado: OperarioEstado

    maquinas: List["Maquina"] = Relationship(back_populates="operario")
