from sqlmodel import Field, SQLModel, Relationship
from app.schemas.maquina import MaquinaEstado
from app.schemas.operario import MaquinaTipo, Operario # Asumo que existe en el esquema de operario
import uuid
from typing import Optional

class Maquina(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    codigo: str = Field(index=True, unique=True)
    tipo: MaquinaTipo
    nombre: str
    descripcion: Optional[str] = None
    modelo: Optional[str] = None
    capacidad_por_hora: float
    estado: MaquinaEstado
    
    operario_asignado_id: Optional[uuid.UUID] = Field(default=None, foreign_key="operario.id")
    operario: Optional["Operario"] = Relationship(back_populates="maquinas")
