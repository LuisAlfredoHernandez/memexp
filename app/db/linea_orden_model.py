from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import List, Optional, TYPE_CHECKING
from app.schemas.orden import Talla

if TYPE_CHECKING:
    from .linea_orden_insumo_link import LineaOrdenInsumoLink
    from .orden_model import Orden
    from app.schemas.orden import InsumoRequerido

class LineaOrden(SQLModel, table=True):
    __tablename__ = "linea_orden"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    producto_tipo: Optional[str] = None
    descripcion: str
    cantidad: int
    cantidad_completada: int = Field(default=0)
    talla: Talla
    color: Optional[str] = None
    orden_id: uuid.UUID = Field(foreign_key="orden.id")
    orden: "Orden" = Relationship(back_populates="lineas")
    insumo_links: List["LineaOrdenInsumoLink"] = Relationship(back_populates="linea_orden")
    
    @property
    def insumos(self) -> List["InsumoRequerido"]:
        from app.schemas.orden import InsumoRequerido
        return [
            InsumoRequerido(
                insumo_id=link.insumo_id,
                cantidad_requerida=link.cantidad_requerida,
                unidad=link.unidad
            )
            for link in self.insumo_links
        ]
