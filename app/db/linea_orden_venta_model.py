from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .orden_venta_model import OrdenVenta
    from .prenda_model import Prenda

class LineaOrdenVenta(SQLModel, table=True):
    __tablename__ = "linea_orden_venta"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    orden_venta_id: uuid.UUID = Field(foreign_key="orden_venta.id", index=True)
    prenda_id: Optional[uuid.UUID] = Field(default=None, foreign_key="prenda.id")
    descripcion: str
    talla: str
    color: Optional[str] = None
    cantidad: int
    precio_unitario: float = Field(default=0.0)

    orden_venta: "OrdenVenta" = Relationship(back_populates="lineas")
    prenda: Optional["Prenda"] = Relationship()
