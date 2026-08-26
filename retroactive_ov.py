import sys
import os

# Ajustar el path para que pueda importar 'app'
sys.path.insert(0, "/")

from sqlmodel import Session, select
from app.db.session import engine
from app.db.orden_model import Orden
from app.db.orden_venta_model import OrdenVenta, EstadoOrdenVenta
from app.db.linea_orden_model import LineaOrden
from app.db.linea_orden_venta_model import LineaOrdenVenta
from app.db.prenda_model import Prenda
import re
from datetime import datetime, timezone

def run_migration():
    with Session(engine) as db:
        ordenes = db.exec(select(Orden).where(Orden.orden_venta_id == None)).all()
        if not ordenes:
            print("No hay órdenes de producción sin Orden de Venta vinculada.")
            return

        print(f"Migrando {len(ordenes)} órdenes de producción...")
        
        # Obtener el número máximo actual
        todos_numeros = db.exec(select(OrdenVenta.numero)).all()
        max_num = 0
        for num_str in todos_numeros:
            match = re.search(r"\d+$", num_str)
            if match:
                num = int(match.group())
                if num > max_num:
                    max_num = num

        count = 0
        for orden in ordenes:
            max_num += 1
            numero_ov = f"OV-{max_num:03d}"
            
            # Determinar estado de la OV basado en la OP
            estado_ov = EstadoOrdenVenta.EN_PRODUCCION
            if str(orden.estado.value).upper() == "COMPLETADA":
                estado_ov = EstadoOrdenVenta.COMPLETADA
            elif str(orden.estado.value).upper() == "CANCELADA":
                estado_ov = EstadoOrdenVenta.CANCELADA
            
            # Crear Orden de Venta
            ov = OrdenVenta(
                numero=numero_ov,
                cliente=orden.cliente,
                estado=estado_ov,
                prioridad=orden.prioridad,
                fecha_entrega_estimada=orden.fecha_entrega_estimada,
                notas=f"Auto-generada desde {orden.numero}. {orden.notas or ''}",
                fecha_creacion=orden.fecha_creacion
            )
            db.add(ov)
            db.flush()
            
            # Vincular OP a la nueva OV
            orden.orden_venta_id = ov.id
            db.add(orden)
            
            # Migrar líneas de la orden
            for linea_op in orden.lineas:
                # Buscar prenda_id basado en descripcion (que ahora es el nombre de la prenda en la lógica anterior)
                prenda_id = None
                if linea_op.descripcion:
                    # Intenta encontrar prenda
                    from sqlmodel import func
                    prenda = db.exec(select(Prenda).where(func.lower(Prenda.nombre) == func.lower(linea_op.descripcion))).first()
                    if prenda:
                        prenda_id = prenda.id

                linea_ov = LineaOrdenVenta(
                    orden_venta_id=ov.id,
                    prenda_id=prenda_id,
                    descripcion=linea_op.descripcion,
                    talla=linea_op.talla,
                    color=linea_op.color,
                    cantidad=linea_op.cantidad,
                    precio_unitario=0.0 # Se asume 0 para histórico
                )
                db.add(linea_ov)
            count += 1
            
        db.commit()
        print(f"¡Migración completada! Se crearon {count} órdenes de venta retroactivamente.")

if __name__ == "__main__":
    run_migration()
