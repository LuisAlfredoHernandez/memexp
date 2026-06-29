from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from app.schemas.asignacion import AsignacionResponse, AsignacionCreate, AsignacionUpdate
from app.db.asignacion_model import AsignacionOrden
from app.db.orden_model import Orden
from app.db.operario_model import Operario
from app.db.usuario_model import Usuario
from app.db.session import get_session
from app.api.deps import get_current_active_user
from app.schemas.usuario import Rol
from app.core.websocket import manager
import uuid

router = APIRouter(prefix="/asignaciones", tags=["Planta - Asignaciones"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[AsignacionResponse])
def listar_asignaciones(
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    if current_user.rol == Rol.Operario:
        asignaciones = db.exec(select(AsignacionOrden).where(AsignacionOrden.operario_id == current_user.id)).all()
    else:
        asignaciones = db.exec(select(AsignacionOrden)).all()
    return asignaciones

@router.post("/", response_model=AsignacionResponse, status_code=status.HTTP_201_CREATED)
def crear_asignacion(
    asignacion: AsignacionCreate,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    if current_user.rol not in [Rol.Administrador, Rol.Supervisor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para crear asignaciones."
        )
    
    # Validar que existe la orden
    db_orden = db.get(Orden, asignacion.orden_id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
        
    # Validar que existe el operario
    db_operario = db.get(Operario, asignacion.operario_id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")
        
    db_asignacion = AsignacionOrden(**asignacion.model_dump())
    db.add(db_asignacion)
    db.commit()
    db.refresh(db_asignacion)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {"event": "assignment_updated"})
    return db_asignacion

@router.patch("/{id}", response_model=AsignacionResponse)
def actualizar_asignacion(
    id: uuid.UUID,
    asignacion_update: AsignacionUpdate,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    db_asignacion = db.get(AsignacionOrden, id)
    if not db_asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
        
    update_data = asignacion_update.model_dump(exclude_unset=True)
    
    if current_user.rol == Rol.Operario:
        # Validar pertenencia
        if db_asignacion.operario_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puede modificar asignaciones de otros operarios."
            )
        # Operario solo puede actualizar piezas_completadas y estado
        for key in list(update_data.keys()):
            if key not in ["piezas_completadas", "estado"]:
                update_data.pop(key)
    elif current_user.rol not in [Rol.Administrador, Rol.Supervisor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para modificar asignaciones."
        )
        
    for key, value in update_data.items():
        setattr(db_asignacion, key, value)
        
    db.add(db_asignacion)
    db.commit()
    db.refresh(db_asignacion)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {"event": "assignment_updated"})
    return db_asignacion

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_asignacion(
    id: uuid.UUID,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None
):
    if current_user.rol not in [Rol.Administrador, Rol.Supervisor]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para eliminar asignaciones."
        )
        
    db_asignacion = db.get(AsignacionOrden, id)
    if not db_asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")
        
    db.delete(db_asignacion)
    db.commit()
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {"event": "assignment_updated"})
    return
