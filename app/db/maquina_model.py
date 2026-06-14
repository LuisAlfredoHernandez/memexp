from sqlmodel import Field, SQLModel, Relationship
from app.schemas.maquina import MaquinaEstado
from app.schemas.operario import MaquinaTipo
import uuid
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .operario_model import Operario

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
