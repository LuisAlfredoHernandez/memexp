from pydantic import BaseModel, Field
from typing import Optional, Any

# --- Petición de tiempo de entrega (RF12) ---
class PredictionRequest(BaseModel):
    cantidad_piezas: int = Field(..., gt=0, description="Cantidad total de piezas a fabricar")
    prioridad_alta: bool = Field(default=False, description="¿Es un pedido urgente?")
    lineas_produccion: int = Field(default=1, gt=0, description="Líneas de ensamblaje asignadas")
    tipo_prenda: str = Field(..., description="Tipo de prenda a confeccionar (ej: corbata, camiseta, pantalon)")

class PredictionResponse(BaseModel):
    tiempo_estimado_horas: Optional[float] = None
    margen_error_horas: Optional[float] = None
    modelo_version: str
    prenda_nueva: bool
    algoritmo_usado: str
    fuera_de_rango: bool = False

# --- Esquemas para predicciones de órdenes multilínea ---
class PredictionRequestItem(BaseModel):
    tipo_prenda: str = Field(..., description="Tipo de prenda (ej: camiseta)")
    cantidad_piezas: int = Field(..., gt=0, description="Cantidad de piezas para este tipo de prenda")

class OrderPredictionRequest(BaseModel):
    lineas_produccion: int = Field(default=1, gt=0, description="Líneas de producción asignadas para toda la orden")
    prioridad_alta: bool = Field(default=False, description="¿Es un pedido urgente?")
    items: list[PredictionRequestItem] = Field(..., description="Lista de prendas y cantidades")

class ItemPredictionDetail(BaseModel):
    tipo_prenda: str
    cantidad_piezas: int
    tiempo_estimado_horas: Optional[float] = None
    margen_error_horas: Optional[float] = None
    prenda_nueva: bool
    fuera_de_rango: bool = False

class OrderPredictionResponse(BaseModel):
    tiempo_estimado_total_horas: Optional[float] = None
    margen_error_total_horas: Optional[float] = None
    prenda_nueva_global: bool
    detalles: list[ItemPredictionDetail]

# --- Petición de Simulación MTS (RF16) ---
class MtsSimulationRequest(BaseModel):
    cantidad_piezas: int = Field(..., gt=0, description="Cantidad total de la orden de stock (MTS)")

class MtsSimulationItem(BaseModel):
    orden: str
    antes: str
    despues: str
    impacto: str
    color: str
    fuera_de_rango: bool = False

# --- Gestión / Reentrenamiento (RF19–RF22) ---
class TrainResponse(BaseModel):
    estado: str
    registros_entrenados: int
    mae_actual: Optional[float] = None
    mse_actual: Optional[float] = None
    mae_nuevo: float
    mse_nuevo: float
    version_publicada: str

# --- Seed Helper ---
class SeedResponse(BaseModel):
    estado: str
    mensaje: str
    registros_insertados: int
