from pydantic import BaseModel, Field
from datetime import datetime
from enum import str, Enum

class EstadoOrden(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"

class InsumoRequerido(BaseModel):
    insumo_id: str
    cantidad_requerida: float
    unidad: str

class TipoOP(str, Enum):
    MTO="MTO"
    MTS="MTS"

class Temporada(str, Enum):
    PRIMAVERA = "P"
    VERANO = "V"
    OTONO= "O"
    INVIERNO = "I"
    PERMANENTE = "permanente"

class LineaOrden(BaseModel):
    producto_tipo: str | None = None
    descripcion: str
    cantidad: int = Field(..., gt=0)
    cantidad_completada: int = 0
    talla: str
    color: str | None = None
    insumos: list[InsumoRequerido] = []

class OrdenBase(BaseModel):
    numero: str = Field(..., min_length=1)
    cliente: str = Field(..., min_length=2)
    tipo: TipoOP
    estado: EstadoOrden
    prioridad: str
    temporada: Temporada | None = None 
    fecha_entrega_estimada: datetime
    notas: str | None = None
    cola: int | None = Field(default=None, ge=0)
    lineas: list[LineaOrden] = Field(..., min_length=1)

class Orden(OrdenBase):
    id: str | None = None
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    creada_por: str | None = None

    class ConfigDict:
        from_attributes = True

class OrdenCreate(OrdenBase):
    pass

class OrdenUpdate(OrdenBase):
    pass    