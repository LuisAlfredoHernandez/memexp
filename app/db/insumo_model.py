import uuid
from sqlmodel import Field, SQLModel, Relationship
from typing import List, TYPE_CHECKING
from app.schemas.insumo import TipoInsumo, UnidadMedida

if TYPE_CHECKING:
    from .linea_orden_insumo_link import LineaOrdenInsumoLink


class Insumo(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nombre: str = Field(..., min_length=1, unique=True)
    codigo: str | None = Field(default=None, index=True)
    tipo: TipoInsumo
    unidad: UnidadMedida
    stock: float = Field(default=0)
    minimo: float = Field(default=0)
    proveedor: str | None = None
    vinculado_a: List["LineaOrdenInsumoLink"] = Relationship(back_populates="insumo")
