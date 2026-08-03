from fastapi import APIRouter, status, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from app.schemas.operario import Operario as OperarioSchema, OperarioCreate, OperarioUpdate
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.db.operario_model import Operario
from app.db.usuario_model import Usuario
from app.db.asignacion_model import AsignacionOrden
from app.db.maquina_model import Maquina
from app.schemas.maquina import MaquinaEstado
from app.db.session import get_session
from app.core.security import hash_password
from app.api.deps import get_current_active_user
from app.core.websocket import manager
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/operarios", tags=["Planta - Operarios"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[OperarioSchema])
def listar_operarios(db: Session = Depends(get_session)):
    operarios = db.exec(select(Operario)).all()
    return operarios

@router.post("/", response_model=OperarioSchema, status_code=status.HTTP_201_CREATED)
def crear_operario(
    operario: OperarioCreate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    user_create = UsuarioCreate.model_validate(operario.model_dump())
    
    hashed_password = hash_password(user_create.password)
    
    db_usuario = Usuario.model_validate(user_create, update={"hashed_password": hashed_password})
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    
    # 2. Crear el registro de Operario, usando el ID del usuario.
    operario_data = operario.model_dump(exclude={"nombre", "apellido", "correo", "password", "rol", "estado"})
    db_operario = Operario(id=db_usuario.id, **operario_data)
    
    db.add(db_operario)
    db.commit()
    db.refresh(db_operario)
    
    # Asignar la relación de usuario para que Pydantic pueda leer las properties
    db_operario.usuario = db_usuario
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "operator_updated",
            "usuario_id": str(current_user.id)
        })
    return db_operario

@router.get("/{id}", response_model=OperarioSchema)
def obtener_operario(id: uuid.UUID, db: Session = Depends(get_session)):
    db_operario = db.get(Operario, id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")
    return db_operario

@router.patch("/{id}", response_model=OperarioSchema)
def actualizar_operario(
    id: uuid.UUID,
    operario: OperarioUpdate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    db_operario = db.get(Operario, id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")

    # Es crucial cargar el usuario para poder modificarlo
    db_usuario = db_operario.usuario
    if not db_usuario:
        raise HTTPException(status_code=500, detail="Inconsistencia de datos: Operario sin usuario asociado.")

    update_data = operario.model_dump(exclude_unset=True)

    # 1. Actualizar campos específicos del modelo Operario
    operario_specific_fields = ['habilidades', 'orden_actual_id']
    for field in operario_specific_fields:
        if field in update_data:
            setattr(db_operario, field, update_data[field])

    # 1.5 Manejar sincronización de maquina_actual_id con validación de concurrencia
    reasignacion_info = None
    if "maquina_actual_id" in update_data:
        new_maquina_id = update_data["maquina_actual_id"]
        old_maquina_id = db_operario.maquina_actual_id
        
        if new_maquina_id != old_maquina_id:
            # Liberar la máquina antigua
            if old_maquina_id:
                old_maquina = db.get(Maquina, old_maquina_id)
                if old_maquina:
                    old_maquina.operario_asignado_id = None
                    db.add(old_maquina)
            
            # Asignar la nueva máquina
            if new_maquina_id:
                new_maquina = db.get(Maquina, new_maquina_id)
                if not new_maquina:
                    raise HTTPException(status_code=404, detail="La nueva máquina no existe.")
                
                if new_maquina.estado != MaquinaEstado.OPERATIVA:
                    raise HTTPException(status_code=400, detail="Conflicto: La máquina ya no está operativa.")
                if new_maquina.operario_asignado_id is not None and new_maquina.operario_asignado_id != db_operario.id:
                    raise HTTPException(status_code=409, detail="Conflicto: La máquina acaba de ser asignada a otro operario.")
                
                new_maquina.operario_asignado_id = db_operario.id
                db.add(new_maquina)
                
                reasignacion_info = {
                    "operario_id": str(db_operario.id),
                    "nueva_maquina_id": str(new_maquina.id),
                    "nueva_maquina_codigo": new_maquina.codigo,
                    "nueva_maquina_nombre": new_maquina.nombre
                }
                
            db_operario.maquina_actual_id = new_maquina_id

    # 2. Actualizar campos del modelo Usuario subyacente
    user_update_fields = UsuarioUpdate.model_fields.keys()
    for field in user_update_fields:
        if field in update_data:
            value = update_data[field]
            if field == "password" and value:
                db_usuario.hashed_password = hash_password(value)
            elif field != "password":
                setattr(db_usuario, field, value)

    db.add(db_usuario)
    db.commit()
    db.refresh(db_operario)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "operator_updated",
            "usuario_id": str(current_user.id)
        })
        
        if "maquina_actual_id" in update_data:
            background_tasks.add_task(manager.broadcast, {
                "event": "machine_updated"
            })
            if reasignacion_info:
                background_tasks.add_task(manager.broadcast, {
                    "event": "reasignacion_maquina",
                    **reasignacion_info
                })
    return db_operario

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_operario(
    id: uuid.UUID,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    db_operario = db.get(Operario, id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")
        
    tiene_asignaciones = db.exec(
        select(AsignacionOrden).where(AsignacionOrden.operario_id == id)
    ).first() is not None

    if tiene_asignaciones:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es posible eliminar físicamente al operario porque cuenta con asignaciones o reportes de trabajo históricos. Por favor, cambie su estado a 'inactivo' en lugar de borrarlo."
        )
    
    db.delete(db_operario)
    db.delete(db_operario.usuario) # La relación debe estar cargada
    db.commit()
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "operator_updated",
            "usuario_id": str(current_user.id)
        })
    return

@router.post("/me/iniciar-sesion", response_model=OperarioSchema)
def iniciar_sesion_trabajo(
    db: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_active_user)
):
    if current_user.rol != "operario":
        raise HTTPException(status_code=403, detail="Solo los operarios pueden iniciar sesión de trabajo.")
        
    db_operario = current_user.operario
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado.")
        
    db_operario.sesion_activa_desde = datetime.now(timezone.utc)
    db.add(db_operario)
    db.commit()
    db.refresh(db_operario)
    return db_operario