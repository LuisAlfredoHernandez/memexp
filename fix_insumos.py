
from sqlmodel import Session, select
from app.db.session import engine
from app.db.linea_orden_model import LineaOrden
from app.db.insumo_model import Insumo
from app.db.linea_orden_insumo_link import LineaOrdenInsumoLink
from app.schemas.insumo import UnidadMedida
import random
import uuid

def fix():
    with Session(engine) as db:
        # Get all insumos
        insumos = db.exec(select(Insumo)).all()
        if not insumos:
            print("No insumos found, creating a dummy one...")
            dummy_insumo = Insumo(
                id=uuid.uuid4(),
                nombre="Hilo Dummy",
                categoria="hilos",
                codigo="DUMMY-01",
                cantidad=1000,
                unidad=UnidadMedida.METROS,
                stock_minimo=10,
                costo_unitario=1.0
            )
            db.add(dummy_insumo)
            db.commit()
            db.refresh(dummy_insumo)
            insumos = [dummy_insumo]
        
        # Get all lineas
        lineas = db.exec(select(LineaOrden)).all()
        added_count = 0
        for linea in lineas:
            # Check if has links
            links = db.exec(select(LineaOrdenInsumoLink).where(LineaOrdenInsumoLink.linea_orden_id == linea.id)).all()
            if not links:
                insumo = random.choice(insumos)
                link = LineaOrdenInsumoLink(
                    linea_orden_id=linea.id,
                    insumo_id=insumo.id,
                    cantidad_requerida=round(random.uniform(1.0, 50.0), 2),
                    unidad=insumo.unidad
                )
                db.add(link)
                added_count += 1
                print(f"Added insumo {insumo.nombre} to LineaOrden {linea.id}")
        
        db.commit()
        print(f"Fixed {added_count} lineas.")

if __name__ == "__main__":
    fix()

