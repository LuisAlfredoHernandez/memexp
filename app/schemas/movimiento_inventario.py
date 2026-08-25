from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from enum import Enum


class TipoMovimiento(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"


class MovimientoInventarioBase(BaseModel):
    tipo_movimiento: TipoMovimiento
    cantidad: float
    referencia: str | None = None
    justificacion: str | None = None


class MovimientoInventarioCreate(MovimientoInventarioBase):
    insumo_id: UUID


class MovimientoInventario(MovimientoInventarioBase):
    id: UUID
    insumo_id: UUID
    fecha: datetime

    model_config = {"from_attributes": True}
