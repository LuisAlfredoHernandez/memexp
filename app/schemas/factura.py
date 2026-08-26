from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid

from .orden_venta import OrdenVenta, LineaOrdenVenta


class EstadoFactura(str, Enum):
    PENDIENTE = "PENDIENTE"
    PROCESADA = "PROCESADA"


class FacturaBase(BaseModel):
    orden_venta_id: uuid.UUID
    notas: str | None = None


class FacturaCreate(FacturaBase):
    """Solo se necesita el ID de la Orden de Venta; el total se calcula automáticamente."""
    pass


class Factura(BaseModel):
    id: uuid.UUID
    numero: str
    orden_venta_id: uuid.UUID
    estado: EstadoFactura
    subtotal: float
    impuesto: float
    total: float
    notas: str | None = None
    fecha_emision: datetime
    fecha_procesamiento: datetime | None = None

    model_config = {"from_attributes": True}


class FacturaDetalle(Factura):
    """Incluye los datos completos de la Orden de Venta para la vista de impresión."""
    orden_venta: OrdenVenta

    model_config = {"from_attributes": True}
