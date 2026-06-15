from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from app.schemas.maquina import Maquina as MaquinaSchema, MaquinaCreate, MaquinaUpdate, MaquinaEstado
from app.db.maquina_model import Maquina
from app.db.session import get_session
from app.api.deps import get_current_active_user
import uuid

router = APIRouter(prefix="/maquinas", tags=["Planta - Maquinaria"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[MaquinaSchema])
def listar_maquinas(db: Session = Depends(get_session)):
    maquinas = db.exec(select(Maquina)).all()
    return maquinas

@router.post("/", response_model=MaquinaSchema, status_code=status.HTTP_201_CREATED)
def crear_maquina(maquina: MaquinaCreate, db: Session = Depends(get_session)):
    db_maquina = Maquina.model_validate(maquina)
    db.add(db_maquina)
    db.commit()
    db.refresh(db_maquina)
    return db_maquina

@router.get("/{id}", response_model=MaquinaSchema)
def obtener_maquina(id: uuid.UUID, db: Session = Depends(get_session)):
    db_maquina = db.get(Maquina, id)
    if not db_maquina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Máquina no encontrada")
    return db_maquina

@router.patch("/{id}", response_model=MaquinaSchema)
def actualizar_maquina(id: uuid.UUID, maquina: MaquinaUpdate, db: Session = Depends(get_session)):
    db_maquina = db.get(Maquina, id)
    if not db_maquina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Máquina no encontrada")
    
    maquina_data = maquina.model_dump(exclude_unset=True)
    for key, value in maquina_data.items():
        setattr(db_maquina, key, value)
        
    db.add(db_maquina)
    db.commit()
    db.refresh(db_maquina)
    return db_maquina

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_maquina(id: uuid.UUID, db: Session = Depends(get_session)):
    db_maquina = db.get(Maquina, id)
    if not db_maquina:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Máquina no encontrada")
    db_maquina.estado = MaquinaEstado.FUERA_SERVICIO
    db.add(db_maquina)
    db.commit()
    return