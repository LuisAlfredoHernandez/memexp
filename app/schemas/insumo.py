from pydantic import BaseModel, Field
from enum import Enum
import uuid

class TipoInsumo(str, Enum):
    TELA = "tela"
    ZIPPER = "zipper"
    GOMA = "goma"
    BOTON = "boton"
    HILO = "hilo"
    OTRO = "otro"

class UnidadMedida(str, Enum):
    METROS = "metros"
    UNIDADES = "unidades"
    ROLLOS = "rollos"
    KG = "kg"

class _OrdenInfoParaInsumo(BaseModel):
    """Información básica de una orden para el contexto de un insumo."""
    id: uuid.UUID
    numero: str

    class ConfigDict:
        from_attributes = True

class _LineaOrdenInfoParaInsumo(BaseModel):
    """Información de una línea de orden para el contexto de un insumo."""
    id: uuid.UUID
    orden: _OrdenInfoParaInsumo

    class ConfigDict:
        from_attributes = True

class InsumoEnOrden(BaseModel):
    """Describe cómo y dónde se utiliza un insumo, en el contexto de una orden."""
    cantidad_requerida: float
    unidad: UnidadMedida
    linea_orden: _LineaOrdenInfoParaInsumo

    class ConfigDict:
        from_attributes = True

class InsumoBase(BaseModel):
    nombre: str = Field(..., min_length=1)
    codigo: str | None = None
    tipo: TipoInsumo
    unidad: UnidadMedida
    stock: float = Field(default=0, ge=0)
    minimo: float = Field(default=0, ge=0)
    proveedor: str | None = None

class InsumoCreate(InsumoBase):
    pass

class Insumo(InsumoBase):
    id: uuid.UUID
    vinculado_a: list[InsumoEnOrden] = Field(default_factory=list)

    class ConfigDict:
        from_attributes = True


class InsumoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1)
    codigo: str | None = None
    tipo: TipoInsumo | None = None
    unidad: UnidadMedida | None = None
    stock: float | None = Field(default=None, ge=0)
    minimo: float | None = Field(default=None, ge=0)
    proveedor: str | None = None
