from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from app.schemas.factura import (
    Factura as FacturaSchema,
    FacturaDetalle,
    EstadoFactura,
)
from app.db.factura_model import Factura as FacturaDB
from app.db.orden_venta_model import OrdenVenta as OrdenVentaDB, EstadoOrdenVenta
from app.db.session import get_session
from app.api.deps import get_current_active_user
import uuid

router = APIRouter(
    prefix="/facturas",
    tags=["Finanzas - Facturación"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get("/", response_model=list[FacturaDetalle])
def listar_facturas(
    estado: EstadoFactura | None = None,
    db: Session = Depends(get_session),
):
    query = select(FacturaDB).options(selectinload(FacturaDB.orden_venta))
    if estado:
        query = query.where(FacturaDB.estado == estado)
    facturas = db.exec(query).all()
    return [FacturaDetalle.model_validate(f) for f in facturas]


@router.get("/{id}", response_model=FacturaDetalle)
def obtener_factura(id: uuid.UUID, db: Session = Depends(get_session)):
    """Devuelve la factura con todos los datos de la Orden de Venta incluidos (para impresión)."""
    factura = db.get(FacturaDB, id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return FacturaDetalle.model_validate(factura)


@router.patch("/{id}/procesar", response_model=FacturaSchema)
def procesar_factura(id: uuid.UUID, db: Session = Depends(get_session)):
    """
    Marca una factura como PROCESADA.
    Efecto secundario: Actualiza la Orden de Venta vinculada a estado FACTURADA.
    """
    factura = db.get(FacturaDB, id)
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    if factura.estado == EstadoFactura.PROCESADA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta factura ya fue procesada.",
        )

    # Procesar la factura
    factura.estado = EstadoFactura.PROCESADA
    factura.fecha_procesamiento = datetime.now(timezone.utc)
    db.add(factura)

    # Efecto secundario: actualizar la OV a FACTURADA
    db_ov = db.get(OrdenVentaDB, factura.orden_venta_id)
    if db_ov:
        db_ov.estado = EstadoOrdenVenta.FACTURADA
        db.add(db_ov)

    db.commit()
    db.refresh(factura)
    return FacturaSchema.model_validate(factura)
