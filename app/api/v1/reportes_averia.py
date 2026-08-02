from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from app.schemas.reporte_averia import ReporteAveriaResponse, ReporteAveriaCreate, ReporteAveriaProcesar
from app.db.reporte_averia_model import ReporteAveria
from app.db.maquina_model import Maquina
from app.db.operario_model import Operario
from app.db.session import get_session
from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario, Rol
from app.schemas.maquina import MaquinaEstado
from app.core.websocket import manager
import uuid

router = APIRouter(prefix="/reportes-averia", tags=["Planta - Reportes de Avería"], dependencies=[Depends(get_current_active_user)])

def build_response(r: ReporteAveria) -> ReporteAveriaResponse:
    op_name = f"{r.operario.nombre} {r.operario.apellido}".strip() if r.operario else ""
    maq_cod = r.maquina.codigo if r.maquina else ""
    maq_nom = r.maquina.nombre if r.maquina else ""
    maq_tipo = r.maquina.tipo.value if r.maquina and r.maquina.tipo else None
    
    return ReporteAveriaResponse(
        id=r.id,
        maquina_id=r.maquina_id,
        operario_id=r.operario_id,
        descripcion=r.descripcion,
        tipo_falla=r.tipo_falla,
        gravedad=r.gravedad,
        detiene_produccion=r.detiene_produccion,
        estado=r.estado,
        fecha_reporte=r.fecha_reporte,
        operario_nombre=op_name,
        maquina_codigo=maq_cod,
        maquina_nombre=maq_nom,
        maquina_tipo=maq_tipo
    )

@router.get("/", response_model=list[ReporteAveriaResponse])
def listar_reportes_averia(db: Session = Depends(get_session)):
    reportes = db.exec(select(ReporteAveria)).all()
    return [build_response(r) for r in reportes]

@router.get("/pendientes", response_model=list[ReporteAveriaResponse])
def listar_reportes_averia_pendientes(
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    if current_user.rol not in [Rol.Administrador, Rol.Supervisor, Rol.Operario]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para consultar reportes de avería pendientes."
        )
    reportes = db.exec(select(ReporteAveria).where(ReporteAveria.estado == "pendiente")).all()
    return [build_response(r) for r in reportes]

@router.post("/", response_model=ReporteAveriaResponse, status_code=status.HTTP_201_CREATED)
def crear_reporte_averia(
    reporte: ReporteAveriaCreate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    db_maquina = db.get(Maquina, reporte.maquina_id)
    if not db_maquina:
        raise HTTPException(status_code=404, detail="Máquina no encontrada")
        
    db_operario = db.get(Operario, reporte.operario_id)
    if not db_operario:
        db_operario = db.exec(select(Operario).where(Operario.id == current_user.id)).first()
        if db_operario:
            reporte.operario_id = db_operario.id
        else:
            raise HTTPException(status_code=404, detail="Operario no encontrado")

    db_reporte = ReporteAveria(**reporte.model_dump())
    db.add(db_reporte)
    
    # Al crear el reporte de avería, la máquina pasa inmediatamente a estado BAJO_REVISION
    db_maquina.estado = MaquinaEstado.BAJO_REVISION
    db.add(db_maquina)
    
    db.commit()
    db.refresh(db_reporte)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "reporte_averia_created",
            "usuario_id": str(current_user.id),
            "maquina_id": str(db_maquina.id),
            "maquina_codigo": db_maquina.codigo,
            "maquina_tipo": db_maquina.tipo,
            "estado_maquina": db_maquina.estado
        })
    return build_response(db_reporte)

@router.post("/{id}/procesar", response_model=ReporteAveriaResponse)
def procesar_reporte_averia(
    id: uuid.UUID,
    payload: ReporteAveriaProcesar,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    if current_user.rol not in [Rol.Administrador, Rol.Supervisor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para procesar reportes de avería."
        )

    db_reporte = db.get(ReporteAveria, id)
    if not db_reporte:
        raise HTTPException(status_code=404, detail="Reporte de avería no encontrado")

    db_maquina = db.get(Maquina, db_reporte.maquina_id)

    reasignacion_info = None

    if payload.aprobado:
        db_reporte.estado = "aprobado"
        if db_maquina:
            db_maquina.estado = MaquinaEstado.FUERA_SERVICIO
            
            # Desvincular al operario de la máquina dañada
            if db_maquina.operario_asignado_id:
                operario_id = db_maquina.operario_asignado_id
                operario = db.get(Operario, operario_id)
                db_maquina.operario_asignado_id = None
                if operario:
                    operario.maquina_actual_id = None
                    db.add(operario)
                
                # Reasignar si se proporciona nueva_maquina_id
                if payload.nueva_maquina_id:
                    nueva_maquina = db.get(Maquina, payload.nueva_maquina_id)
                    if not nueva_maquina:
                        raise HTTPException(status_code=400, detail="La nueva máquina seleccionada no existe.")
                    if nueva_maquina.estado != MaquinaEstado.OPERATIVA:
                        raise HTTPException(status_code=400, detail="La nueva máquina seleccionada no está operativa.")
                    if nueva_maquina.tipo != db_maquina.tipo:
                        raise HTTPException(status_code=400, detail="La nueva máquina debe ser del mismo tipo que la averiada.")
                    if nueva_maquina.operario_asignado_id is not None:
                        raise HTTPException(status_code=400, detail="La nueva máquina ya tiene un operario asignado.")
                        
                    nueva_maquina.operario_asignado_id = operario_id
                    if operario:
                        operario.maquina_actual_id = nueva_maquina.id
                        db.add(operario)
                    db.add(nueva_maquina)
                    
                    reasignacion_info = {
                        "operario_id": str(operario_id),
                        "nueva_maquina_id": str(nueva_maquina.id),
                        "nueva_maquina_codigo": nueva_maquina.codigo,
                        "nueva_maquina_nombre": nueva_maquina.nombre
                    }
                    
            db.add(db_maquina)
    else:
        db_reporte.estado = "rechazado"
        if db_maquina:
            db_maquina.estado = MaquinaEstado.OPERATIVA
            db.add(db_maquina)

    db.add(db_reporte)
    db.commit()
    db.refresh(db_reporte)

    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "reporte_averia_processed",
            "usuario_id": str(current_user.id),
            "reporte_id": str(db_reporte.id),
            "aprobado": payload.aprobado,
            "maquina_id": str(db_maquina.id) if db_maquina else None,
            "estado_maquina": db_maquina.estado if db_maquina else None
        })
        
        if reasignacion_info:
            background_tasks.add_task(manager.broadcast, {
                "event": "reasignacion_maquina",
                **reasignacion_info
            })

    return build_response(db_reporte)
