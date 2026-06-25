from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from typing import Optional

class ReporteAvanceBase(BaseModel):
    asignacion_id: uuid.UUID
    piezas_reportadas: int = Field(..., ge=0, description="Total de piezas a reportar")
    maquina_id: Optional[str] = Field(default=None, description="Identificador de la máquina")
    notas: Optional[str] = Field(default=None, description="Notas del operario")

class ReporteAvanceCreate(ReporteAvanceBase):
    pass

class ReporteAvanceValidar(BaseModel):
    piezas_buenas: int = Field(..., ge=0)
    piezas_defectuosas: int = Field(..., ge=0)
    estado: str = Field(default="validado")  # "validado" o "rechazado"

class ReporteAvanceResponse(BaseModel):
    id: uuid.UUID
    asignacion_id: uuid.UUID
    operario_id: uuid.UUID
    operario_nombre: str
    orden_id: str  # Retorna el número de orden (ej: ORD-2026-0042) para compatibilidad con frontend
    maquina_id: Optional[str] = None
    piezas_reportadas: int
    piezas_buenas: int
    piezas_defectuosas: int
    estado: str
    fecha_reporte: datetime
    notas: Optional[str] = None

    class ConfigDict:
        from_attributes = True
