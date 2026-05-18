from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from app.schemas.insumo import Insumo as InsumoSchema, InsumoCreate, InsumoUpdate
from app.db.insumo_model import Insumo
from app.db.session import get_session
import uuid

router = APIRouter(prefix="/insumos", tags=["Inventario - Insumos"])

@router.get("/", response_model=list[InsumoSchema])
def obtener_insumos(db: Session = Depends(get_session)):
    insumos = db.exec(select(Insumo)).all()
    return insumos

@router.get("/{id}", response_model=InsumoSchema)
def obtener_insumo(id: uuid.UUID, db: Session = Depends(get_session)):
    insumo = db.get(Insumo, id)
    if not insumo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
    return insumo

@router.post("/", response_model=InsumoSchema, status_code=status.HTTP_201_CREATED)
def crear_insumo(insumo: InsumoCreate, db: Session = Depends(get_session)):
    # El modelo de base de datos 'Insumo' se instancia a partir del schema de creación
    db_insumo = Insumo.model_validate(insumo)
    
    # El UUID se genera aquí en el backend gracias al `default_factory=uuid.uuid4` en el modelo
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo

@router.patch("/{id}", response_model=InsumoSchema)
def actualizar_insumo(id: uuid.UUID, insumo: InsumoUpdate, db: Session = Depends(get_session)):
    db_insumo = db.get(Insumo, id)
    if not db_insumo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
    
    insumo_data = insumo.model_dump(exclude_unset=True)
    for key, value in insumo_data.items():
        setattr(db_insumo, key, value)
        
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    return db_insumo

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_insumo(id: uuid.UUID, db: Session = Depends(get_session)):
    insumo = db.get(Insumo, id)
    if not insumo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
    db.delete(insumo)
    db.commit()
    return