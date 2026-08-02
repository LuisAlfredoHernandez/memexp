from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlmodel import Session, select, func
from app.schemas.orden import Orden as OrdenSchema, OrdenCreate, OrdenUpdate, EstadoOrden
from app.db.orden_model import Orden as OrdenDB
from app.db.linea_orden_model import LineaOrden as LineaOrdenDB
from app.db.linea_orden_insumo_link import LineaOrdenInsumoLink
from app.db.insumo_model import Insumo as InsumoDB
from app.db.session import get_session
from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario
from app.core.websocket import manager
from app.db.prenda_model import Prenda
from app.services.ml_engine.pipeline import train_model
from app.services.ml_engine.predictor import predictor
from app.db.asignacion_model import AsignacionOrden
import uuid
import re

router = APIRouter(prefix="/ordenes", tags=["Producción - Órdenes"], dependencies=[Depends(get_current_active_user)])

@router.get("/", response_model=list[OrdenSchema])
def listar_ordenes(db: Session = Depends(get_session)):
    ordenes = db.exec(select(OrdenDB)).all()
    return [OrdenSchema.model_validate(o) for o in ordenes]

@router.get("/prendas", response_model=list[str])
def listar_prendas(db: Session = Depends(get_session)):
    prendas = db.exec(select(Prenda.nombre)).all()
    return prendas

@router.post("/", response_model=OrdenSchema, status_code=status.HTTP_201_CREATED)
def crear_orden(
    orden: OrdenCreate,
    db: Session = Depends(get_session),
    background_tasks: BackgroundTasks = None,
    current_user: Usuario = Depends(get_current_active_user)
):
    orden_data = orden.model_dump()
    lineas_data = orden_data.pop("lineas")
    asignaciones_data = orden_data.pop("asignaciones", [])
    
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
    

    
    # Crea los objetos anidados en memoria. SQLModel los asociará.
    for linea_item in lineas_data:
        insumos_data = linea_item.pop("insumos")
        
        # Registrar prenda si no existe en la BD
        prenda_name = linea_item.get("descripcion", "").strip()
        if prenda_name:
            existente = db.exec(select(Prenda).where(func.lower(Prenda.nombre) == func.lower(prenda_name))).first()
            if not existente:
                nueva_prenda = Prenda(nombre=prenda_name)
                db.add(nueva_prenda)
                db.commit()
        
        db_linea = LineaOrdenDB(**linea_item, orden=db_orden)
        for insumo_item in insumos_data:
            # Obtener el insumo e ir restando el stock correspondiente
            db_insumo = db.get(InsumoDB, insumo_item["insumo_id"])
            if not db_insumo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Insumo con ID {insumo_item['insumo_id']} no encontrado"
                )

            if insumo_item["unidad"].lower() != db_insumo.unidad.lower():
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

            nuevo_link = LineaOrdenInsumoLink(
                linea_orden=db_linea,
                insumo_id=insumo_item["insumo_id"],
                cantidad_requerida=insumo_item["cantidad_requerida"],
                unidad=insumo_item["unidad"]
            )
            db.add(nuevo_link)
    
    
    db.add(db_orden)
    db.flush() # Para obtener db_orden.id antes del commit
    
    # Crear asignaciones
    for asig_item in asignaciones_data:
        db_asig = AsignacionOrden(
            orden_id=db_orden.id,
            operario_id=asig_item["operario_id"],
            tarea=asig_item["tarea"],
            piezas_requeridas=asig_item["piezas_requeridas"],
            notas=asig_item.get("notas")
        )
        db.add(db_asig)

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
    return OrdenSchema.model_validate(db_orden)

@router.get("/{id}", response_model=OrdenSchema)
def obtener_orden(id: uuid.UUID, db: Session = Depends(get_session)):
    db_orden = db.get(OrdenDB, id)
    if not db_orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return OrdenSchema.model_validate(db_orden)

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
        # 1. Devolver el stock de los insumos anteriores al inventario
        for linea in db_orden.lineas:
            for link in linea.insumo_links:
                db_insumo = db.get(InsumoDB, link.insumo_id)
                if db_insumo:
                    db_insumo.stock += link.cantidad_requerida
                    db.add(db_insumo)

        # Estrategia de reemplazo: Deep Diff
        lineas_data = update_data.pop("lineas")
        existing_lineas = {str(linea.id): linea for linea in db_orden.lineas}
        incoming_lineas_ids = set()
        
        for linea_item in lineas_data:
            linea_id = str(linea_item.pop("id")) if linea_item.get("id") else None
            insumos_data = linea_item.pop("insumos")
            
            # Registrar prenda si no existe en la BD
            prenda_name = linea_item.get("descripcion", "").strip()
            if prenda_name:
                existente = db.exec(select(Prenda).where(func.lower(Prenda.nombre) == func.lower(prenda_name))).first()
                if not existente:
                    nueva_prenda = Prenda(nombre=prenda_name)
                    db.add(nueva_prenda)
                    db.commit()
            
            if linea_id and linea_id in existing_lineas:
                db_linea = existing_lineas[linea_id]
                for key, value in linea_item.items():
                    setattr(db_linea, key, value)
                incoming_lineas_ids.add(linea_id)
            else:
                db_linea = LineaOrdenDB(**linea_item, orden=db_orden)
            
            existing_links = {str(link.insumo_id): link for link in db_linea.insumo_links}
            incoming_insumo_ids = set()

            for insumo_item in insumos_data:
                insumo_id_str = str(insumo_item["insumo_id"])
                incoming_insumo_ids.add(insumo_id_str)
                
                db_insumo = db.get(InsumoDB, insumo_id_str)
                if not db_insumo:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Insumo con ID {insumo_id_str} no encontrado"
                    )

                if insumo_item["unidad"].lower() != db_insumo.unidad.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"La unidad del insumo no coincide con la unidad de la orden"
                    )
                
                # Validar stock suficiente
                if insumo_item["cantidad_requerida"] > db_insumo.stock:
                    print(f"DEBUG: req={insumo_item['cantidad_requerida']} > stock={db_insumo.stock}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"No hay stock suficiente para la orden"
                    )
                
                db_insumo.stock -= insumo_item["cantidad_requerida"]
                db.add(db_insumo)

                if insumo_id_str in existing_links:
                    link = existing_links[insumo_id_str]
                    link.cantidad_requerida = insumo_item["cantidad_requerida"]
                    link.unidad = insumo_item["unidad"]
                else:
                    nuevo_link = LineaOrdenInsumoLink(
                        linea_orden=db_linea,
                        insumo_id=insumo_id_str,
                        cantidad_requerida=insumo_item["cantidad_requerida"],
                        unidad=insumo_item["unidad"]
                    )
                    db.add(nuevo_link)
            
            for ins_id, link in existing_links.items():
                if ins_id not in incoming_insumo_ids:
                    db_linea.insumo_links.remove(link)

        # Eliminar las prendas que ya no están
        for ex_id, ex_linea in existing_lineas.items():
            if ex_id not in incoming_lineas_ids:
                db_orden.lineas.remove(ex_linea)

    if "asignaciones" in update_data:
        asignaciones_data = update_data.pop("asignaciones")
        
        # Mapear asignaciones existentes
        existing_asigs = db.exec(select(AsignacionOrden).where(AsignacionOrden.orden_id == db_orden.id)).all()
        existing_map = {str(a.id): a for a in existing_asigs}
        
        incoming_ids = set()
        
        for asig_item in asignaciones_data:
            asig_id = str(asig_item.get("id")) if asig_item.get("id") else None
            
            if asig_id and asig_id in existing_map:
                # Actualizar existente
                db_asig = existing_map[asig_id]
                db_asig.operario_id = asig_item["operario_id"]
                db_asig.tarea = asig_item["tarea"]
                db_asig.piezas_requeridas = asig_item["piezas_requeridas"]
                db_asig.notas = asig_item.get("notas")
                db.add(db_asig)
                incoming_ids.add(asig_id)
            else:
                # Crear nueva
                db_asig = AsignacionOrden(
                    orden_id=db_orden.id,
                    operario_id=asig_item["operario_id"],
                    tarea=asig_item["tarea"],
                    piezas_requeridas=asig_item["piezas_requeridas"],
                    notas=asig_item.get("notas")
                )
                db.add(db_asig)
                
        # Eliminar las que ya no están en la lista (solo si no han sido comenzadas)
        for ex_id, ex_asig in existing_map.items():
            if ex_id not in incoming_ids:
                if ex_asig.piezas_completadas == 0:
                    db.delete(ex_asig)

    for key, value in update_data.items():
        setattr(db_orden, key, value)

    db.add(db_orden)
    db.commit()
    db.refresh(db_orden)
    
    if db_orden.estado == EstadoOrden.COMPLETADA:
        # Reparar estados huérfanos: Si la orden se completó, sus asignaciones también deben completarse.
        # Esto previene que la IA lea 'asignacion_orden' en proceso que ya finalizaron.
        asignaciones = db.exec(select(AsignacionOrden).where(AsignacionOrden.orden_id == db_orden.id)).all()
        for asig in asignaciones:
            if str(asig.estado).lower() != "completada":
                asig.estado = "completada"
                db.add(asig)
        db.commit()

        # Disparar Sincronización de IA (Opción 1)
        if background_tasks:
            def reentrenar_y_recargar():
                try:
                    train_model()
                    predictor._load_model()
                except Exception as e:
                    print(f"[IA Sync] Error reentrenando modelo en background: {e}")
            
            background_tasks.add_task(reentrenar_y_recargar)

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
    
    if db_orden.estado in [EstadoOrden.EN_PROCESO, EstadoOrden.COMPLETADA]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No es posible eliminar una orden en estado '{db_orden.estado.value}'. Las órdenes activas o completadas forman parte del historial operativo y de calibración de la IA."
        )
        
    # Devolver el stock de los insumos asignados antes de eliminar
    for linea in db_orden.lineas:
        for link in linea.insumo_links:
            db_insumo = db.get(InsumoDB, link.insumo_id)
            if db_insumo:
                db_insumo.stock += link.cantidad_requerida
                db.add(db_insumo)

    db.delete(db_orden)
    db.commit()
    if background_tasks:
        background_tasks.add_task(manager.broadcast, {
            "event": "order_deleted",
            "orden_id": str(id),
            "usuario_id": str(current_user.id)
        })
    return OrdenSchema.model_validate(db_orden)