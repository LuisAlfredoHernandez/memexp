from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from app.schemas.orden_compra import (
    OrdenCompraRead,
    OrdenCompraCreate,
    OrdenCompraUpdate,
    EstadoOrdenCompra,
    LineaOrdenCompra as LineaOrdenCompraSchema,
)
from app.db.orden_compra_model import OrdenCompra as OrdenCompraDB
from app.db.linea_orden_compra_model import LineaOrdenCompra as LineaOrdenCompraDB
from app.db.insumo_model import Insumo as InsumoDB
from app.db.session import get_session
from app.api.deps import get_current_active_user
import uuid
import re

router = APIRouter(
    prefix="/ordenes-compra",
    tags=["Inventario - Órdenes de Compra"],
    dependencies=[Depends(get_current_active_user)],
)


def _generar_numero_oc(db: Session) -> str:
    """Genera un número autoincremental OC-001, OC-002, etc."""
    todos_numeros = db.exec(select(OrdenCompraDB.numero)).all()
    max_num = 0
    for num_str in todos_numeros:
        match = re.search(r"\d+$", num_str)
        if match:
            num = int(match.group())
            if num > max_num:
                max_num = num
    return f"OC-{max_num + 1:03d}"


def _serialize_oc(db_oc: OrdenCompraDB) -> dict:
    """Serializa una OC incluyendo el nombre del insumo en cada línea."""
    oc_dict = OrdenCompraRead.model_validate(db_oc).model_dump()
    for i, linea_db in enumerate(db_oc.lineas):
        if linea_db.insumo:
            oc_dict["lineas"][i]["insumo_nombre"] = linea_db.insumo.nombre
    return oc_dict


@router.get("/", response_model=list[OrdenCompraRead])
def listar_ordenes_compra(db: Session = Depends(get_session)):
    ordenes = db.exec(select(OrdenCompraDB)).all()
    return [_serialize_oc(oc) for oc in ordenes]


@router.get("/{id}", response_model=OrdenCompraRead)
def obtener_orden_compra(id: uuid.UUID, db: Session = Depends(get_session)):
    oc = db.get(OrdenCompraDB, id)
    if not oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    return _serialize_oc(oc)


@router.post("/", response_model=OrdenCompraRead, status_code=status.HTTP_201_CREATED)
def crear_orden_compra(orden: OrdenCompraCreate, db: Session = Depends(get_session)):
    orden_data = orden.model_dump()
    lineas_data = orden_data.pop("lineas")

    numero = _generar_numero_oc(db)
    db_oc = OrdenCompraDB(numero=numero, **orden_data)

    for linea_item in lineas_data:
        # Verificar que el insumo exista
        db_insumo = db.get(InsumoDB, linea_item["insumo_id"])
        if not db_insumo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insumo con ID {linea_item['insumo_id']} no encontrado",
            )
        LineaOrdenCompraDB(**linea_item, orden_compra=db_oc)

    db.add(db_oc)
    db.commit()
    db.refresh(db_oc)
    return _serialize_oc(db_oc)


@router.patch("/{id}", response_model=OrdenCompraRead)
def actualizar_orden_compra(
    id: uuid.UUID,
    orden: OrdenCompraUpdate,
    db: Session = Depends(get_session),
):
    db_oc = db.get(OrdenCompraDB, id)
    if not db_oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")

    if db_oc.estado == EstadoOrdenCompra.RECIBIDA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar una orden de compra ya recibida.",
        )

    update_data = orden.model_dump(exclude_unset=True)

    if "lineas" in update_data:
        lineas_data = update_data.pop("lineas")
        for linea in list(db_oc.lineas):
            db.delete(linea)
        db.flush()

        for linea_item in lineas_data:
            db_insumo = db.get(InsumoDB, linea_item["insumo_id"])
            if not db_insumo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Insumo con ID {linea_item['insumo_id']} no encontrado",
                )
            LineaOrdenCompraDB(**linea_item, orden_compra=db_oc)

    for key, value in update_data.items():
        setattr(db_oc, key, value)

    db.add(db_oc)
    db.commit()
    db.refresh(db_oc)
    return _serialize_oc(db_oc)


@router.patch("/{id}/recibir", response_model=OrdenCompraRead)
def recibir_orden_compra(id: uuid.UUID, db: Session = Depends(get_session)):
    """
    Marca una OC como RECIBIDA y suma las cantidades al stock de cada insumo.
    Esta operación es irreversible.
    """
    db_oc = db.get(OrdenCompraDB, id)
    if not db_oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")

    if db_oc.estado != EstadoOrdenCompra.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden recibir órdenes en estado 'PENDIENTE'. Estado actual: '{db_oc.estado.value}'.",
        )

    # Sumar las cantidades al stock de cada insumo
    for linea in db_oc.lineas:
        db_insumo = db.get(InsumoDB, linea.insumo_id)
        if not db_insumo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insumo con ID {linea.insumo_id} no encontrado al recibir la orden.",
            )
        db_insumo.stock += linea.cantidad
        db.add(db_insumo)

    db_oc.estado = EstadoOrdenCompra.RECIBIDA
    db.add(db_oc)
    db.commit()
    db.refresh(db_oc)
    return _serialize_oc(db_oc)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_orden_compra(id: uuid.UUID, db: Session = Depends(get_session)):
    db_oc = db.get(OrdenCompraDB, id)
    if not db_oc:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")

    if db_oc.estado != EstadoOrdenCompra.PENDIENTE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden eliminar órdenes en estado 'PENDIENTE'. Estado actual: '{db_oc.estado.value}'.",
        )

    db.delete(db_oc)
    db.commit()
