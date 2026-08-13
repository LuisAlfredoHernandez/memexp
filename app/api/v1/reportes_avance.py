from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from datetime import datetime, timezone
import uuid

from app.db.session import get_session
from app.db.usuario_model import Usuario
from app.db.operario_model import Operario
from app.db.asignacion_model import AsignacionOrden
from app.db.reporte_avance_model import ReporteAvance
from app.db.maquina_model import Maquina
from app.schemas.reporte_avance import ReporteAvanceCreate, ReporteAvanceResponse, ReporteAvanceValidar
from app.schemas.usuario import Rol
from app.api.deps import get_current_active_user
from app.core.websocket import manager
from app.services.eficiencia_service import calcular_eficiencia_sesion, actualizar_eficiencia_operario
from app.api.v1.utils_asignaciones import revisar_y_liberar_maquina

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
        fecha_inicio=reporte.fecha_inicio,
        fecha_fin=reporte.fecha_fin,
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
    # Prioridad: 1. Input manual, 2. Sesión activa
    fecha_inicio = payload.fecha_inicio
    fecha_fin = datetime.now(timezone.utc)
    
    db_operario = db.get(Operario, db_asignacion.operario_id)
    if db_operario:
        if not maquina:
            maquina = db_operario.maquina_actual_id
            
        if not fecha_inicio:
            fecha_inicio = db_operario.sesion_activa_desde
            
        # Limpiar la sesión activa en el operario
        db_operario.sesion_activa_desde = None
        db.add(db_operario)
        
    if not fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe iniciar la sesión primero o enviar manualmente la hora de inicio (fecha_inicio)."
        )
            
    db_reporte = ReporteAvance(
        asignacion_id=payload.asignacion_id,
        operario_id=db_asignacion.operario_id,
        piezas_reportadas=payload.piezas_reportadas,
        maquina_id=maquina,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
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
    
    if payload.fecha_inicio is not None:
        db_reporte.fecha_inicio = payload.fecha_inicio
    if payload.fecha_fin is not None:
        db_reporte.fecha_fin = payload.fecha_fin
    
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
            
            # Empujar piezas a la siguiente etapa (Pipeline Secuencial)
            if payload.piezas_buenas > 0:
                siguiente_asig = db.exec(
                    select(AsignacionOrden)
                    .where(AsignacionOrden.orden_id == db_asignacion.orden_id)
                    .where(AsignacionOrden.secuencia == db_asignacion.secuencia + 1)
                ).first()
                if siguiente_asig:
                    siguiente_asig.piezas_habilitadas += payload.piezas_buenas
                    db.add(siguiente_asig)
                else:
                    # ES LA ÚLTIMA TAREA DE LA SECUENCIA: SON PIEZAS TERMINADAS
                    # Iteramos las líneas de la orden para ir llenando su "cantidad_completada" en cascada
                    if db_asignacion.orden and db_asignacion.orden.lineas:
                        piezas_restantes = payload.piezas_buenas
                        for linea in db_asignacion.orden.lineas:
                            faltantes = linea.cantidad - (linea.cantidad_completada or 0)
                            if faltantes > 0 and piezas_restantes > 0:
                                a_sumar = min(faltantes, piezas_restantes)
                                linea.cantidad_completada = (linea.cantidad_completada or 0) + a_sumar
                                piezas_restantes -= a_sumar
                                db.add(linea)
            
            # Automatización de estados de la Orden General
            if db_asignacion.orden:
                orden = db_asignacion.orden
                
                # 1. Arrancarla automáticamente si estaba pendiente
                if orden.estado == "pendiente":
                    orden.estado = "en_proceso"
                
                # 2. Consultar todas las asignaciones de esta misma orden
                todas_asignaciones = db.exec(
                    select(AsignacionOrden)
                    .where(AsignacionOrden.orden_id == orden.id)
                ).all()
                
                # Verificar si en todas las asignaciones las piezas_completadas ya alcanzaron o superaron las piezas_requeridas
                todas_completadas = all(
                    asig.piezas_completadas >= asig.piezas_requeridas 
                    for asig in todas_asignaciones
                )
                
                # Si todas terminaron, cambiamos la orden global a completada
                if todas_completadas:
                    orden.estado = "completada"
                
                db.add(orden)

        # Recalcular eficiencia dinámica del operario para la máquina utilizada
        maquina_val = db_reporte.maquina_id
        if not maquina_val and db_reporte.operario:
            maquina_val = db_reporte.operario.maquina_actual_id

        if maquina_val:
            import uuid
            maq_obj = None
            try:
                maq_uuid = uuid.UUID(str(maquina_val))
                maq_obj = db.exec(select(Maquina).where(Maquina.id == maq_uuid)).first()
            except ValueError:
                pass
            
            if not maq_obj:
                try:
                    # Intenta buscar por tipo o codigo, asumiendo que no es un UUID válido.
                    # Primero validamos si el string es un tipo válido para no explotar la DB
                    from app.schemas.maquina import MaquinaTipo
                    if str(maquina_val) in [e.value for e in MaquinaTipo]:
                        maq_obj = db.exec(select(Maquina).where(Maquina.tipo == str(maquina_val))).first()
                    if not maq_obj:
                        maq_obj = db.exec(select(Maquina).where(Maquina.codigo == str(maquina_val))).first()
                except Exception:
                    pass

            capacidad_hora = float(maq_obj.capacidad_por_hora) if maq_obj and maq_obj.capacidad_por_hora > 0 else 10.0
            maq_tipo = str(maq_obj.tipo if maq_obj else maquina_val.split("-")[0]).lower()

            horas_trabajadas = 1.0
            if db_reporte.fecha_inicio and db_reporte.fecha_fin:
                diff_sec = (db_reporte.fecha_fin - db_reporte.fecha_inicio).total_seconds()
                if diff_sec > 0:
                    horas_trabajadas = max(0.1, diff_sec / 3600.0)
            elif db_asignacion and db_asignacion.fecha_asignacion and db_reporte.fecha_reporte:
                diff_sec = (db_reporte.fecha_reporte - db_asignacion.fecha_asignacion).total_seconds()
                if diff_sec > 0:
                    horas_trabajadas = max(0.1, min(24.0, diff_sec / 3600.0))

            eficiencia_sesion = calcular_eficiencia_sesion(payload.piezas_buenas, horas_trabajadas, capacidad_hora)
            actualizar_eficiencia_operario(db, db_reporte.operario_id, maq_tipo, eficiencia_sesion)
            
    db.add(db_reporte)
    db.commit()
    
    if payload.estado == "validado":
        revisar_y_liberar_maquina(db, db_reporte.operario_id)
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
            "orden_numero": orden_numero,
            "fecha_inicio": db_reporte.fecha_inicio.isoformat() if db_reporte.fecha_inicio else None,
            "fecha_fin": db_reporte.fecha_fin.isoformat() if db_reporte.fecha_fin else None
        })
    return build_response(db_reporte)
