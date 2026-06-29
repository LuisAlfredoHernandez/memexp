from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlmodel import Session, select, func
from app.schemas.orden import Orden as OrdenSchema, OrdenCreate, OrdenUpdate
from app.db.orden_model import Orden as OrdenDB
from app.db.linea_orden_model import LineaOrden as LineaOrdenDB
from app.db.linea_orden_insumo_link import LineaOrdenInsumoLink
from app.db.insumo_model import Insumo as InsumoDB
from app.db.session import get_session
from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario
from app.core.websocket import manager
import uuid
import re

router = APIRouter(prefix="/ordenes", tags=["Producción - Órdenes"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[OrdenSchema])
def listar_ordenes(db: Session = Depends(get_session)):
    ordenes = db.exec(select(OrdenDB)).all()
    return ordenes

@router.post("/", response_model=OrdenSchema, status_code=status.HTTP_201_CREATED)
def crear_orden(
    orden: OrdenCreate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    orden_data = orden.model_dump()
    lineas_data = orden_data.pop("lineas")
    
    # Generar el número de orden autoincremental (OP + TipoOP + número)
    todas_ordenes = db.exec(select(OrdenDB.numero)).all()
    max_num = 0
    for num_str in todas_ordenes:
        match = re.search(r'\d+$', num_str)
        if match:
            num = int(match.group())
            if num > max_num:
                max_num = num
    next_num = max_num + 1
    numero_orden = f"OP{orden.tipo.value}{next_num}"
    
    # Crea el objeto Orden principal
    db_orden = OrdenDB(numero=numero_orden, **orden_data)
    
    # Autoincrementar la cola si no se especifica
    if db_orden.cola is None:
        max_cola = db.exec(select(func.max(OrdenDB.cola))).one()
        db_orden.cola = (max_cola or 0) + 1
    
    # Crea los objetos anidados en memoria. SQLModel los asociará.
    for linea_item in lineas_data:
        insumos_data = linea_item.pop("insumos")
        db_linea = LineaOrdenDB(**linea_item, orden=db_orden)
        for insumo_item in insumos_data:
            # Obtener el insumo e ir restando el stock correspondiente
            db_insumo = db.get(InsumoDB, insumo_item["insumo_id"])
            if not db_insumo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Insumo con ID {insumo_item['insumo_id']} no encontrado"
                )

            if insumo_item["unidad"] != db_insumo.unidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La unidad del insumo no coincide con la unidad de la orden"
                )
            
            # Validar que haya stock suficiente
            if insumo_item["cantidad_requerida"] > db_insumo.stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No hay stock suficiente para la orden"
                )
            
            db_insumo.stock -= insumo_item["cantidad_requerida"]
            db.add(db_insumo)

            _ = LineaOrdenInsumoLink(
                linea_orden=db_linea,
                insumo_id=insumo_item["insumo_id"],
                cantidad_requerida=insumo_item["cantidad_requerida"],
                unidad=insumo_item["unidad"]
            )
    
    db.add(db_orden)
    db.commit()
    db.refresh(db_orden)
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "order_created",
            "orden_id": str(db_orden.id),
            "numero": db_orden.numero,
            "estado": db_orden.estado.value if hasattr(db_orden.estado, "value") else str(db_orden.estado),
            "prioridad": db_orden.prioridad.value if hasattr(db_orden.prioridad, "value") else str(db_orden.prioridad),
            "usuario_id": str(current_user.id)
        })
    return db_orden

@router.get("/{id}", response_model=OrdenSchema)
def obtener_orden(id: uuid.UUID, db: Session = Depends(get_session)):
    db_orden = db.get(OrdenDB, id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return db_orden

@router.patch("/{id}", response_model=OrdenSchema)
def actualizar_orden(
    id: uuid.UUID,
    orden: OrdenUpdate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
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
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "order_updated",
            "orden_id": str(db_orden.id),
            "numero": db_orden.numero,
            "estado": db_orden.estado.value if hasattr(db_orden.estado, "value") else str(db_orden.estado),
            "prioridad": db_orden.prioridad.value if hasattr(db_orden.prioridad, "value") else str(db_orden.prioridad),
            "usuario_id": str(current_user.id)
        })
    return db_orden

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_orden(
    id: uuid.UUID,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    db_orden = db.get(OrdenDB, id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    db.delete(db_orden)
    db.commit()
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "order_deleted",
            "orden_id": str(id),
            "usuario_id": str(current_user.id)
        })
    return