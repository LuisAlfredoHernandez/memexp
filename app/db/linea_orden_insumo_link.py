from sqlmodel import Field, SQLModel, Relationship
import uuid
from typing import TYPE_CHECKING

from app.schemas.insumo import UnidadMedida

if TYPE_CHECKING:
    from .insumo_model import Insumo
    from .linea_orden_model import LineaOrden

class LineaOrdenInsumoLink(SQLModel, table=True):
    __tablename__ = "linea_orden_insumo_link"

    linea_orden_id: uuid.UUID = Field(foreign_key="linea_orden.id", primary_key=True)
    insumo_id: uuid.UUID = Field(foreign_key="insumo.id", primary_key=True)
    
    cantidad_requerida: float
    unidad: UnidadMedida

    linea_orden: "LineaOrden" = Relationship(back_populates="insumo_links")
    insumo: "Insumo" = Relationship(back_populates="vinculado_a")
