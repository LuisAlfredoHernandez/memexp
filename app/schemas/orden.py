from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid

from .insumo import UnidadMedida

class EstadoOrden(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"
    PAUSADA = "pausada"

class InsumoRequerido(BaseModel):
    insumo_id: uuid.UUID
    cantidad_requerida: float
    unidad: UnidadMedida

class TipoOP(str, Enum):
    MTO="MTO"
    MTS="MTS"

class Temporada(str, Enum):
    PRIMAVERA = "Primavera"
    VERANO = "Verano"
    OTONO= "Otono"
    INVIERNO = "Invierno"
    OTRO = "OTRO"

class Talla(str, Enum):
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    UNICA = "UNICA"
    MIXTA = "MIXTA"

class LineaOrden(BaseModel):
    producto_tipo: str | None = None
    descripcion: str
    cantidad: int = Field(..., gt=0)
    cantidad_completada: int | None = 0
    talla: Talla
    color: str | None = None
    insumos: list[InsumoRequerido] = Field(
        default=[],
        json_schema_extra={
            "example": [
                {
                    "insumo_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "cantidad_requerida": 10.5,
                    "unidad": "metros"
                }
            ]
        }
    )

class OrdenBase(BaseModel):
    cliente: str = Field(..., min_length=2)
    tipo: TipoOP
    prioridad: str
    temporada: Temporada | None = None 
    fecha_entrega_estimada: datetime
    notas: str | None = None
    lineas: list[LineaOrden] = Field(..., min_length=1)

    model_config = {
        "json_schema_extra": {
            "example": {
                "cliente": "Distribuidora ACME",
                "tipo": "MTO",
                "prioridad": "alta",
                "temporada": "Primavera",
                "fecha_entrega_estimada": "2026-06-25T14:30:00Z",
                "notas": "Lotes prioritarios para despacho rápido.",
                "lineas": [
                    {
                        "producto_tipo": "camiseta",
                        "descripcion": "Camiseta estampada básica",
                        "cantidad": 50,
                        "cantidad_completada": 0,
                        "talla": "L",
                        "color": "rojo",
                        "insumos": [
                            {
                                "insumo_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "cantidad_requerida": 75.0,
                                "unidad": "metros"
                            }
                        ]
                    }
                ]
            }
        }
    }

class Orden(OrdenBase):
    id: uuid.UUID
    numero: str
    estado: EstadoOrden
    cola: int | None = None
    fecha_creacion: datetime = Field(default_factory=datetime.now)

    class ConfigDict:
        from_attributes = True

class OrdenCreate(OrdenBase):
    pass

class OrdenUpdate(BaseModel):
    cliente: str | None = Field(default=None, min_length=2)
    tipo: TipoOP | None = None
    estado: EstadoOrden | None = None
    prioridad: str | None = None
    temporada: Temporada | None = None
    fecha_entrega_estimada: datetime | None = None
    notas: str | None = None
    cola: int | None = Field(default=None, ge=0)
    lineas: list[LineaOrden] | None = Field(default=None, min_length=1)