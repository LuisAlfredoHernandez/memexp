from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .orden_compra_model import OrdenCompra
    from .insumo_model import Insumo

class LineaOrdenCompra(SQLModel, table=True):
    __tablename__ = "linea_orden_compra"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    orden_compra_id: uuid.UUID = Field(foreign_key="orden_compra.id", index=True)
    insumo_id: uuid.UUID = Field(foreign_key="insumo.id", index=True)
    cantidad: float
    precio_unitario: float = Field(default=0.0)

    orden_compra: "OrdenCompra" = Relationship(back_populates="lineas")
    insumo: Optional["Insumo"] = Relationship()
