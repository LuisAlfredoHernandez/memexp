from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class EstadoOrdenVenta(str, Enum):
    EN_ESPERA = "EN_ESPERA"
    EN_PRODUCCION = "EN_PRODUCCION"
    COMPLETADA = "COMPLETADA"
    FACTURADA = "FACTURADA"
    CANCELADA = "CANCELADA"


class LineaOrdenVentaBase(BaseModel):
    prenda_id: uuid.UUID | None = None
    descripcion: str = Field(..., min_length=2)
    talla: str
    color: str | None = None
    cantidad: int = Field(..., gt=0)
    precio_unitario: float = Field(default=0.0, ge=0)


class LineaOrdenVenta(LineaOrdenVentaBase):
    id: uuid.UUID

    model_config = {"from_attributes": True}


class OrdenVentaBase(BaseModel):
    cliente: str = Field(..., min_length=2)
    prioridad: str = Field(default="normal")
    fecha_entrega_estimada: datetime
    notas: str | None = None
    lineas: list[LineaOrdenVentaBase] = Field(..., min_length=1)


class OrdenVentaCreate(OrdenVentaBase):
    pass


class OrdenVenta(BaseModel):
    id: uuid.UUID
    numero: str
    cliente: str
    estado: EstadoOrdenVenta
    prioridad: str
    fecha_entrega_estimada: datetime
    notas: str | None = None
    fecha_creacion: datetime
    lineas: list[LineaOrdenVenta] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrdenVentaUpdate(BaseModel):
    cliente: str | None = Field(default=None, min_length=2)
    prioridad: str | None = None
    estado: EstadoOrdenVenta | None = None
    fecha_entrega_estimada: datetime | None = None
    notas: str | None = None
    lineas: list[LineaOrdenVentaBase] | None = Field(default=None, min_length=1)
