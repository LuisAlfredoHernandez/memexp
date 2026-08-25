from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from app.schemas.orden_venta import (
    OrdenVenta as OrdenVentaSchema,
    OrdenVentaCreate,
    OrdenVentaUpdate,
    EstadoOrdenVenta,
)
from app.schemas.factura import Factura as FacturaSchema, EstadoFactura
from app.db.orden_venta_model import OrdenVenta as OrdenVentaDB
from app.db.linea_orden_venta_model import LineaOrdenVenta as LineaOrdenVentaDB
from app.db.factura_model import Factura as FacturaDB
from app.db.prenda_model import Prenda
from app.db.session import get_session
from app.api.deps import get_current_active_user
from sqlmodel import func
import uuid
import re

router = APIRouter(
    prefix="/ordenes-venta",
    tags=["Comercial - Órdenes de Venta"],
    dependencies=[Depends(get_current_active_user)],
)


def _generar_numero_ov(db: Session) -> str:
    """Genera un número autoincremental OV-001, OV-002, etc."""
    todos_numeros = db.exec(select(OrdenVentaDB.numero)).all()
    max_num = 0
    for num_str in todos_numeros:
        match = re.search(r"\d+$", num_str)
        if match:
            num = int(match.group())
            if num > max_num:
                max_num = num
    return f"OV-{max_num + 1:03d}"


@router.get("/", response_model=list[OrdenVentaSchema])
def listar_ordenes_venta(db: Session = Depends(get_session)):
    ordenes = db.exec(select(OrdenVentaDB)).all()
    return [OrdenVentaSchema.model_validate(ov) for ov in ordenes]


@router.get("/{id}", response_model=OrdenVentaSchema)
def obtener_orden_venta(id: uuid.UUID, db: Session = Depends(get_session)):
    ov = db.get(OrdenVentaDB, id)
    if not ov:
        raise HTTPException(status_code=404, detail="Orden de venta no encontrada")
    return OrdenVentaSchema.model_validate(ov)


@router.post("/", response_model=OrdenVentaSchema, status_code=status.HTTP_201_CREATED)
def crear_orden_venta(orden: OrdenVentaCreate, db: Session = Depends(get_session)):
    orden_data = orden.model_dump()
    lineas_data = orden_data.pop("lineas")

    numero = _generar_numero_ov(db)
    db_ov = OrdenVentaDB(numero=numero, **orden_data)

    for linea_item in lineas_data:
        # Registrar prenda si no existe
        prenda_name = linea_item.get("descripcion", "").strip()
        if prenda_name:
            existente = db.exec(
                select(Prenda).where(func.lower(Prenda.nombre) == func.lower(prenda_name))
            ).first()
            if not existente:
                nueva_prenda = Prenda(nombre=prenda_name)
                db.add(nueva_prenda)
                db.flush()
                linea_item["prenda_id"] = nueva_prenda.id
            elif not linea_item.get("prenda_id"):
                linea_item["prenda_id"] = existente.id

        LineaOrdenVentaDB(**linea_item, orden_venta=db_ov)

    db.add(db_ov)
    db.commit()
    db.refresh(db_ov)
    return OrdenVentaSchema.model_validate(db_ov)


@router.patch("/{id}", response_model=OrdenVentaSchema)
def actualizar_orden_venta(
    id: uuid.UUID,
    orden: OrdenVentaUpdate,
    db: Session = Depends(get_session),
):
    db_ov = db.get(OrdenVentaDB, id)
    if not db_ov:
        raise HTTPException(status_code=404, detail="Orden de venta no encontrada")

    if db_ov.estado == EstadoOrdenVenta.FACTURADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede modificar una orden de venta ya facturada.",
        )

    update_data = orden.model_dump(exclude_unset=True)

    if "lineas" in update_data:
        lineas_data = update_data.pop("lineas")
        # Reemplazar líneas completas (estrategia simple)
        for linea in list(db_ov.lineas):
            db.delete(linea)
        db.flush()

        for linea_item in lineas_data:
            prenda_name = linea_item.get("descripcion", "").strip()
            if prenda_name:
                existente = db.exec(
                    select(Prenda).where(func.lower(Prenda.nombre) == func.lower(prenda_name))
                ).first()
                if not existente:
                    nueva_prenda = Prenda(nombre=prenda_name)
                    db.add(nueva_prenda)
                    db.flush()
                    linea_item["prenda_id"] = nueva_prenda.id
                elif not linea_item.get("prenda_id"):
                    linea_item["prenda_id"] = existente.id

            LineaOrdenVentaDB(**linea_item, orden_venta=db_ov)

    for key, value in update_data.items():
        setattr(db_ov, key, value)

    db.add(db_ov)
    db.commit()
    db.refresh(db_ov)
    return OrdenVentaSchema.model_validate(db_ov)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_orden_venta(id: uuid.UUID, db: Session = Depends(get_session)):
    db_ov = db.get(OrdenVentaDB, id)
    if not db_ov:
        raise HTTPException(status_code=404, detail="Orden de venta no encontrada")

    if db_ov.estado not in [EstadoOrdenVenta.EN_ESPERA, EstadoOrdenVenta.CANCELADA]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede eliminar una orden de venta en estado '{db_ov.estado.value}'. "
            "Solo se pueden eliminar órdenes en espera o canceladas.",
        )

    # Verificar que no tenga órdenes de producción vinculadas
    if db_ov.ordenes_produccion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar esta orden de venta porque tiene órdenes de producción vinculadas.",
        )

    db.delete(db_ov)
    db.commit()


@router.post("/{id}/generar-factura", response_model=FacturaSchema, status_code=status.HTTP_201_CREATED)
def generar_factura(id: uuid.UUID, db: Session = Depends(get_session)):
    """Genera una factura a partir de una Orden de Venta completada."""
    db_ov = db.get(OrdenVentaDB, id)
    if not db_ov:
        raise HTTPException(status_code=404, detail="Orden de venta no encontrada")

    if db_ov.estado != EstadoOrdenVenta.COMPLETADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se puede facturar una orden de venta en estado 'COMPLETADA'. Estado actual: '{db_ov.estado.value}'.",
        )

    # Verificar que no exista ya una factura para esta OV
    factura_existente = db.exec(
        select(FacturaDB).where(FacturaDB.orden_venta_id == id)
    ).first()
    if factura_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una factura (#{factura_existente.numero}) para esta orden de venta.",
        )

    # Calcular totales desde las líneas de la OV
    subtotal = sum(linea.precio_unitario * linea.cantidad for linea in db_ov.lineas)
    impuesto = 0.0  # Se puede parametrizar en el futuro
    total = subtotal + impuesto

    # Generar número de factura
    todos_numeros = db.exec(select(FacturaDB.numero)).all()
    max_num = 0
    for num_str in todos_numeros:
        match = re.search(r"\d+$", num_str)
        if match:
            num = int(match.group())
            if num > max_num:
                max_num = num
    numero_factura = f"FAC-{max_num + 1:03d}"

    db_factura = FacturaDB(
        numero=numero_factura,
        orden_venta_id=id,
        subtotal=subtotal,
        impuesto=impuesto,
        total=total,
    )
    db.add(db_factura)
    db.commit()
    db.refresh(db_factura)
    return FacturaSchema.model_validate(db_factura)
