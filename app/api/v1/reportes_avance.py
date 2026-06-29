from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from datetime import datetime, timezone
import uuid

from app.db.session import get_session
from app.db.usuario_model import Usuario
from app.db.operario_model import Operario
from app.db.asignacion_model import AsignacionOrden
from app.db.reporte_avance_model import ReporteAvance
from app.schemas.reporte_avance import ReporteAvanceCreate, ReporteAvanceResponse, ReporteAvanceValidar
from app.schemas.usuario import Rol
from app.api.deps import get_current_active_user
from app.core.websocket import manager

router = APIRouter(prefix="/reportes-avance", tags=["Planta - Reportes de Avance"], dependencies=[Depends(get_current_active_user)])

def build_response(reporte: ReporteAvance) -> ReporteAvanceResponse:
    nombre = ""
    apellido = ""
    if reporte.operario:
        nombre = reporte.operario.nombre
        apellido = reporte.operario.apellido
    operario_nombre = f"{nombre} {apellido}".strip()
    
    orden_numero = ""
    if reporte.asignacion and reporte.asignacion.orden:
        orden_numero = reporte.asignacion.orden.numero
        
    return ReporteAvanceResponse(
        id=reporte.id,
        asignacion_id=reporte.asignacion_id,
        operario_id=reporte.operario_id,
        operario_nombre=operario_nombre,
        orden_id=orden_numero,
        maquina_id=reporte.maquina_id,
        piezas_reportadas=reporte.piezas_reportadas,
        piezas_buenas=reporte.piezas_buenas,
        piezas_defectuosas=reporte.piezas_defectuosas,
        estado=reporte.estado,
        fecha_reporte=reporte.fecha_reporte,
        notas=reporte.notas
    )

@router.post("/", response_model=ReporteAvanceResponse, status_code=status.HTTP_201_CREATED)
def crear_reporte_avance(
    payload: ReporteAvanceCreate,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    # Validar que existe la asignación
    db_asignacion = db.get(AsignacionOrden, payload.asignacion_id)
    if not db_asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación no encontrada."
        )
        
    # Si es operario, validar pertenencia
    if current_user.rol == Rol.Operario:
        if db_asignacion.operario_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede reportar avances para asignaciones de otros operarios."
            )
            
    # Si maquina_id no se provee, usar la maquinaActual del operario
    maquina = payload.maquina_id
    if not maquina:
        db_operario = db.get(Operario, db_asignacion.operario_id)
        if db_operario:
            maquina = db_operario.maquinaActual
            
    db_reporte = ReporteAvance(
        asignacion_id=payload.asignacion_id,
        operario_id=db_asignacion.operario_id,
        piezas_reportadas=payload.piezas_reportadas,
        maquina_id=maquina,
        notas=payload.notas,
        estado="pendiente"
    )
    
    db.add(db_reporte)
    db.commit()
    db.refresh(db_reporte)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "reporte_avance_created",
            "usuario_id": str(current_user.id)
        })
    return build_response(db_reporte)

@router.get("/pendientes", response_model=list[ReporteAvanceResponse])
def listar_reportes_pendientes(
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    if current_user.rol not in [Rol.Administrador, Rol.Supervisor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para ver reportes de avance pendientes."
        )
        
    reportes = db.exec(select(ReporteAvance).where(ReporteAvance.estado == "pendiente")).all()
    return [build_response(r) for r in reportes]

@router.post("/{id}/validar", response_model=ReporteAvanceResponse)
def validar_reporte_avance(
    id: uuid.UUID,
    payload: ReporteAvanceValidar,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    if current_user.rol not in [Rol.Administrador, Rol.Supervisor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para validar reportes de avance."
        )
        
    db_reporte = db.get(ReporteAvance, id)
    if not db_reporte:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reporte de avance no encontrado."
        )
        
    if db_reporte.estado != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este reporte de avance ya ha sido validado o procesado."
        )
        
    if payload.estado not in ["validado", "rechazado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El estado de validación debe ser 'validado' o 'rechazado'."
        )
        
    # Actualizar reporte
    db_reporte.piezas_buenas = payload.piezas_buenas
    db_reporte.piezas_defectuosas = payload.piezas_defectuosas
    db_reporte.estado = payload.estado
    db_reporte.fecha_validacion = datetime.now(timezone.utc)
    
    # Consolidar avance si es validado
    db_asignacion = db.get(AsignacionOrden, db_reporte.asignacion_id)
    orden_numero = db_asignacion.orden.numero if db_asignacion and db_asignacion.orden else ""
    
    if payload.estado == "validado":
        if db_asignacion:
            db_asignacion.piezas_completadas += payload.piezas_buenas
            
            # Ajustar estado de asignación según el avance completado
            if db_asignacion.piezas_completadas >= db_asignacion.piezas_requeridas:
                db_asignacion.estado = "completada"
            else:
                db_asignacion.estado = "en_proceso"
                
            db.add(db_asignacion)
            
    db.add(db_reporte)
    db.commit()
    db.refresh(db_reporte)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "reporte_avance_validated",
            "usuario_id": str(current_user.id),
            "operario_id": str(db_reporte.operario_id),
            "estado": payload.estado,
            "piezas_reportadas": db_reporte.piezas_reportadas,
            "piezas_buenas": payload.piezas_buenas,
            "piezas_defectuosas": payload.piezas_defectuosas,
            "orden_numero": orden_numero
        })
    return build_response(db_reporte)
