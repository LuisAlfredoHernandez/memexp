import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from typing import TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from app.db.insumo_model import Insumo


class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"


class MovimientoInventario(SQLModel, table=True):
    __tablename__ = "movimiento_inventario"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    insumo_id: uuid.UUID = Field(foreign_key="insumo.id", index=True)
    tipo_movimiento: TipoMovimiento = Field(default=TipoMovimiento.AJUSTE)
    cantidad: float = Field(..., description="Cantidad positiva (entrada) o negativa (salida/merma)")
    fecha: datetime = Field(default_factory=datetime.utcnow)
    referencia: str | None = Field(default=None, description="Ej. OC-001, OP-045")
    justificacion: str | None = Field(default=None, description="Requerida para ajustes manuales")

    # Relación de vuelta al insumo
    insumo: "Insumo" = Relationship(back_populates="movimientos")
