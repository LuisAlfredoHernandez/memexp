from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from app.schemas.orden import Orden as OrdenSchema, OrdenCreate, OrdenUpdate
from app.db.orden_model import Orden as OrdenDB
from app.db.linea_orden_model import LineaOrden as LineaOrdenDB
from app.db.linea_orden_insumo_link import LineaOrdenInsumoLink
from app.db.session import get_session
import uuid

router = APIRouter(prefix="/ordenes", tags=["Producción - Órdenes"])

@router.get("/", response_model=list[OrdenSchema])
def listar_ordenes(db: Session = Depends(get_session)):
    ordenes = db.exec(select(OrdenDB)).all()
    return ordenes

@router.post("/", response_model=OrdenSchema, status_code=status.HTTP_201_CREATED)
def crear_orden(orden: OrdenCreate, db: Session = Depends(get_session)):
    orden_data = orden.model_dump()
    lineas_data = orden_data.pop("lineas")
    
    # Crea el objeto Orden principal
    db_orden = OrdenDB(**orden_data)
    
    # Crea los objetos anidados en memoria. SQLModel los asociará.
    for linea_item in lineas_data:
        insumos_data = linea_item.pop("insumos")
        db_linea = LineaOrdenDB(**linea_item, orden=db_orden)
        for insumo_item in insumos_data:
            _ = LineaOrdenInsumoLink(
                linea_orden=db_linea,
                insumo_id=insumo_item["insumo_id"],
                cantidad_requerida=insumo_item["cantidad_requerida"],
                unidad=insumo_item["unidad"]
            )
    
    db.add(db_orden)
    db.commit()
    db.refresh(db_orden)
    return db_orden

@router.get("/{id}", response_model=OrdenSchema)
def obtener_orden(id: uuid.UUID, db: Session = Depends(get_session)):
    db_orden = db.get(OrdenDB, id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return db_orden

@router.patch("/{id}", response_model=OrdenSchema)
def actualizar_orden(id: uuid.UUID, orden: OrdenUpdate, db: Session = Depends(get_session)):
    db_orden = db.get(OrdenDB, id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    update_data = orden.model_dump(exclude_unset=True)

    if "lineas" in update_data:
        # Estrategia de reemplazo: eliminar líneas antiguas y crear nuevas.
        # Se requiere cascade delete en la BD para que esto sea eficiente.
        for linea in db_orden.lineas:
            db.delete(linea)
        
        lineas_data = update_data.pop("lineas")
        for linea_item in lineas_data:
            insumos_data = linea_item.pop("insumos")
            db_linea = LineaOrdenDB(**linea_item, orden=db_orden)
            for insumo_item in insumos_data:
                _ = LineaOrdenInsumoLink(**insumo_item, linea_orden=db_linea)

    for key, value in update_data.items():
        setattr(db_orden, key, value)

    db.add(db_orden)
    db.commit()
    db.refresh(db_orden)
    return db_orden

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_orden(id: uuid.UUID, db: Session = Depends(get_session)):
    db_orden = db.get(OrdenDB, id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    db.delete(db_orden)
    db.commit()
    return