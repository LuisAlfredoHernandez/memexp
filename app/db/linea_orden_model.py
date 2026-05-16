from app.db.linea_orden_insumo_link import LineaOrdenInsumoLink
from app.db.orden_model import Orden
from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import List, Optional

class LineaOrden(SQLModel, table=True):
    __tablename__ = "linea_orden"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    producto_tipo: Optional[str] = None
    descripcion: str
    cantidad: int
    cantidad_completada: int = Field(default=0)
    talla: str
    color: Optional[str] = None

    orden_id: uuid.UUID = Field(foreign_key="orden.id")
    orden: "Orden" = Relationship(back_populates="lineas")

    insumo_links: List["LineaOrdenInsumoLink"] = Relationship(back_populates="linea_orden")
