from fastapi import APIRouter, status, Depends, HTTPException
from sqlmodel import Session, select
from app.schemas.operario import Operario as OperarioSchema, OperarioCreate, OperarioUpdate
from app.schemas.usuario import UsuarioCreate
from app.db.operario_model import Operario
from app.db.usuario_model import Usuario
from app.db.session import get_session
from app.core.security import hash_password
import uuid

router = APIRouter(prefix="/operarios", tags=["Planta - Operarios"])

@router.get("/", response_model=list[OperarioSchema])
def listar_operarios(db: Session = Depends(get_session)):
    operarios = db.exec(select(Operario)).all()
    return operarios

@router.post("/", response_model=OperarioSchema, status_code=status.HTTP_201_CREATED)
def crear_operario(operario: OperarioCreate, db: Session = Depends(get_session)):
    user_create = UsuarioCreate.model_validate(operario)
    
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
    return db_operario

@router.get("/{id}", response_model=OperarioSchema)
def obtener_operario(id: uuid.UUID, db: Session = Depends(get_session)):
    db_operario = db.get(Operario, id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")
    return db_operario

@router.patch("/{id}", response_model=OperarioSchema)
def actualizar_operario(id: uuid.UUID, operario: OperarioUpdate, db: Session = Depends(get_session)):
    db_operario = db.get(Operario, id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")

    # Es crucial cargar el usuario para poder modificarlo
    db_usuario = db_operario.usuario
    if not db_usuario:
        raise HTTPException(status_code=500, detail="Inconsistencia de datos: Operario sin usuario asociado.")

    update_data = operario.model_dump(exclude_unset=True)

    # 1. Actualizar campos específicos del modelo Operario
    operario_specific_fields = ['habilidades', 'maquinaActual', 'orden_actual_id']
    for field in operario_specific_fields:
        if field in update_data:
            setattr(db_operario, field, update_data[field])

    # 2. Actualizar campos del modelo Usuario subyacente
    user_update_fields = UsuarioUpdate.model_fields.keys()
    for field in user_update_fields:
        if field in update_data:
            value = update_data[field]
            if field == "password" and value:
                db_usuario.hashed_password = hash_password(value)
            elif field != "password":
                setattr(db_usuario, field, value)

    db.add(db_operario)
    db.add(db_usuario)
    db.commit()
    db.refresh(db_operario)
    
    return db_operario

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_operario(id: uuid.UUID, db: Session = Depends(get_session)):
    # Al eliminar un operario, también eliminamos el usuario asociado.
    db_operario = db.get(Operario, id)
    if not db_operario:
        raise HTTPException(status_code=404, detail="Operario no encontrado")
    
    db.delete(db_operario)
    db.delete(db_operario.usuario) # La relación debe estar cargada
    db.commit()
    return