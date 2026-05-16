from app.db.linea_orden_model import LineaOrden
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
import uuid
from typing import List, Optional

from app.schemas.orden import EstadoOrden, TipoOP, Temporada

class Orden(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    numero: str = Field(index=True, unique=True)
    cliente: str
    tipo: TipoOP
    estado: EstadoOrden
    prioridad: str
    temporada: Optional[Temporada] = None
    fecha_entrega_estimada: datetime
    notas: Optional[str] = None
    cola: Optional[int] = None
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    creada_por_id: Optional[uuid.UUID] = Field(default=None, foreign_key="usuario.id")

    lineas: List["LineaOrden"] = Relationship(back_populates="orden")
