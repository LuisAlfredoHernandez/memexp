from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid


class EstadoOrdenCompra(str, Enum):
    PENDIENTE = "PENDIENTE"
    RECIBIDA = "RECIBIDA"
    CANCELADA = "CANCELADA"


class LineaOrdenCompraBase(BaseModel):
    insumo_id: uuid.UUID
    cantidad: float = Field(..., gt=0)
    precio_unitario: float = Field(default=0.0, ge=0)


class LineaOrdenCompra(LineaOrdenCompraBase):
    id: uuid.UUID
    insumo_nombre: str | None = None

    model_config = {"from_attributes": True}


class OrdenCompraBase(BaseModel):
    proveedor: str = Field(..., min_length=2)
    notas: str | None = None
    lineas: list[LineaOrdenCompraBase] = Field(..., min_length=1)


class OrdenCompraCreate(OrdenCompraBase):
    pass


class OrdenCompraRead(BaseModel):
    id: uuid.UUID
    numero: str
    proveedor: str
    estado: EstadoOrdenCompra
    notas: str | None = None
    fecha_creacion: datetime
    lineas: list[LineaOrdenCompra] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class OrdenCompraUpdate(BaseModel):
    proveedor: str | None = Field(default=None, min_length=2)
    estado: EstadoOrdenCompra | None = None
    notas: str | None = None
    lineas: list[LineaOrdenCompraBase] | None = Field(default=None, min_length=1)
