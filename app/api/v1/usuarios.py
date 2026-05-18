from fastapi import APIRouter, status, Depends, HTTPException
from sqlmodel import Session, select
from app.schemas.usuario import Usuario as UsuarioSchema, UsuarioCreate, UsuarioUpdate
from app.db.usuario_model import Usuario
from app.db.session import get_session
from app.core.security import hash_password
import uuid

router = APIRouter(prefix="/usuarios", tags=["Administración - Usuarios"])

@router.get("/", response_model=list[UsuarioSchema])
def listar_usuarios(db: Session = Depends(get_session)):
    usuarios = db.exec(select(Usuario)).all()
    return usuarios

@router.post("/", response_model=UsuarioSchema, status_code=status.HTTP_201_CREATED)
def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_session)):
    hashed_password = hash_password(usuario.password)
    
    extra_data = {"hashed_password": hashed_password}
    db_usuario = Usuario.model_validate(usuario, update=extra_data)
    
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.get("/{id}", response_model=UsuarioSchema)
def obtener_usuario(id: uuid.UUID, db: Session = Depends(get_session)):
    db_usuario = db.get(Usuario, id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_usuario

@router.patch("/{id}", response_model=UsuarioSchema)
def actualizar_usuario(id: uuid.UUID, usuario: UsuarioUpdate, db: Session = Depends(get_session)):
    db_usuario = db.get(Usuario, id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    update_data = usuario.model_dump(exclude_unset=True)
    
    if "password" in update_data and update_data["password"]:
        hashed_password = hash_password(update_data["password"])
        db_usuario.hashed_password = hashed_password
        del update_data["password"]
        
    for key, value in update_data.items():
        setattr(db_usuario, key, value)
        
    db.add(db_usuario)
    db.commit()
    db.refresh(db_usuario)
    return db_usuario

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(id: uuid.UUID, db: Session = Depends(get_session)):
    db_usuario = db.get(Usuario, id)
    if not db_usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(db_usuario)
    db.commit()
    return
