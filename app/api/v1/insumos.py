from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from app.schemas.insumo import Insumo as InsumoSchema, InsumoCreate, InsumoUpdate, AjusteInsumo
from app.db.insumo_model import Insumo
from app.db.movimiento_inventario_model import MovimientoInventario, TipoMovimiento
from app.db.linea_orden_insumo_link import LineaOrdenInsumoLink
from app.db.session import get_session
from app.api.deps import get_current_active_user
import uuid

router = APIRouter(prefix="/insumos", tags=["Inventario - Insumos"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[InsumoSchema])
def obtener_insumos(db: Session = Depends(get_session)):
    insumos = db.exec(select(Insumo).options(selectinload(Insumo.movimientos), selectinload(Insumo.vinculado_a))).all()
    # Sort movimientos by date desc for each insumo
    for insumo in insumos:
        insumo.movimientos.sort(key=lambda m: m.fecha, reverse=True)
    return insumos

@router.get("/{id}", response_model=InsumoSchema)
def obtener_insumo(id: uuid.UUID, db: Session = Depends(get_session)):
    insumo = db.exec(select(Insumo).where(Insumo.id == id).options(selectinload(Insumo.movimientos), selectinload(Insumo.vinculado_a))).first()
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

@router.post("/{id}/ajuste", response_model=InsumoSchema)
def ajustar_stock_insumo(id: uuid.UUID, ajuste: AjusteInsumo, db: Session = Depends(get_session)):
    db_insumo = db.exec(select(Insumo).where(Insumo.id == id).options(selectinload(Insumo.movimientos), selectinload(Insumo.vinculado_a))).first()
    if not db_insumo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
    
    nuevo_stock = db_insumo.stock + ajuste.cantidad_ajuste
    if nuevo_stock < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El ajuste resultaría en un stock negativo.")
        
    db_insumo.stock = nuevo_stock
    
    movimiento = MovimientoInventario(
        insumo_id=id,
        tipo_movimiento=TipoMovimiento.AJUSTE,
        cantidad=ajuste.cantidad_ajuste,
        justificacion=ajuste.justificacion
    )
    db.add(movimiento)
    db.add(db_insumo)
    db.commit()
    db.refresh(db_insumo)
    db_insumo.movimientos.sort(key=lambda m: m.fecha, reverse=True)
    return db_insumo

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_insumo(id: uuid.UUID, db: Session = Depends(get_session)):
    insumo = db.get(Insumo, id)
    if not insumo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insumo no encontrado")
        
    tiene_enlaces = db.exec(
        select(LineaOrdenInsumoLink).where(LineaOrdenInsumoLink.insumo_id == id)
    ).first() is not None

    if tiene_enlaces:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No es posible eliminar el insumo porque está asociado a líneas de orden existentes. Por favor, modifique su stock a 0 o márquelo como inhabilitado para futuras órdenes."
        )
        
    db.delete(insumo)
    db.commit()
    return