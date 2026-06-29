from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from app.schemas.reporte_averia import ReporteAveriaResponse, ReporteAveriaCreate
from app.db.reporte_averia_model import ReporteAveria
from app.db.maquina_model import Maquina
from app.db.session import get_session
from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario
from app.schemas.maquina import MaquinaEstado
from app.core.websocket import manager
import uuid

router = APIRouter(prefix="/reportes-averia", tags=["Planta - Reportes de Avería"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[ReporteAveriaResponse])
def listar_reportes_averia(
    db: Session = Depends(get_session)
):
    reportes = db.exec(select(ReporteAveria)).all()
    return reportes

@router.post("/", response_model=ReporteAveriaResponse, status_code=status.HTTP_201_CREATED)
def crear_reporte_averia(
    reporte: ReporteAveriaCreate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    # Validar que existe la máquina
    db_maquina = db.get(Maquina, reporte.maquina_id)
    if not db_maquina:
        raise HTTPException(status_code=404, detail="Máquina no encontrada")
        
    db_reporte = ReporteAveria(**reporte.model_dump())
    db.add(db_reporte)
    
    # Actualizar estado de la máquina a mantenimiento
    db_maquina.estado = MaquinaEstado.MANTENIMIENTO
    db.add(db_maquina)
    
    db.commit()
    db.refresh(db_reporte)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {"event": "reporte_averia_created"})
    return db_reporte
