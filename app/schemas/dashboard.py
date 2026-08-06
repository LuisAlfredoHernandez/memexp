from pydantic import BaseModel
from typing import List

class DashboardDailyStat(BaseModel):
    d: str
    real: int
    meta: int
    mto: int
    mts: int
    eficiencia: int

class DashboardMachineStat(BaseModel):
    codigo: str
    tipo: str
    uso: int
    estado: str
    piezasSemana: int

class DashboardOperatorStat(BaseModel):
    nombre: str
    eficiencia: int
    piezasSemana: int
    estado: str

class DashboardDistribucion(BaseModel):
    nombre: str
    valor: int
    color: str

class DashboardStatsResponse(BaseModel):
    datos_semana: List[DashboardDailyStat]
    maquinas_uso: List[DashboardMachineStat]
    operarios_rendimiento: List[DashboardOperatorStat]
    distribucion_maquinas: List[DashboardDistribucion]

