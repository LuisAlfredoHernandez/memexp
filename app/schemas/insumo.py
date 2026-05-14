from pydantic import BaseModel, Field
from enum import str, Enum

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

class InsumoBase(BaseModel):
    nombre: str = Field(..., min_length=1)
    codigo: str | None = None
    tipo: TipoInsumo
    unidad: UnidadMedida
    stock: float = Field(default=0, ge=0)
    minimo: float = Field(default=0, ge=0)
    proveedor: str | None = None
    vinculado_a: list[str] = []

class InsumoCreate(InsumoBase):
    pass

class Insumo(InsumoBase):
    id: str

    class ConfigDict:
        from_attributes = True


class InsumoUpdate(InsumoBase):
    pass