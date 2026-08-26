from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List
import uuid
import random
import io
import json
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlmodel import Session

from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario, Rol
from app.db.session import engine, get_session

# Importar esquemas
from app.schemas.predict import (
    PredictionRequest, PredictionResponse,
    MtsSimulationRequest, MtsSimulationItem,
    TrainResponse, SeedResponse,
    OrderPredictionRequest, OrderPredictionResponse,
    ItemPredictionDetail, PredictionRequestItem
)

# Importar servicios
from app.services.ml_engine.predictor import predictor
from app.services.ml_engine.pipeline import train_model
from app.services.eficiencia_service import calcular_eficiencia_sesion, actualizar_eficiencia_operario

router = APIRouter(prefix="/ia", tags=["IA Predictiva"])

@router.post("/predict/delivery-time", response_model=PredictionResponse)
def predecir_tiempo_entrega(
    request: PredictionRequest,
    current_user: Usuario = Depends(get_current_active_user)
):
    """Estima el tiempo de entrega de una asignación en horas (RF12)"""
    try:
        tiempo, error, prenda_nueva, fuera_de_rango = predictor.predict(
            cantidad_piezas=request.cantidad_piezas,
            prioridad_alta=request.prioridad_alta,
            lineas_produccion=request.lineas_produccion,
            tipo_prenda=request.tipo_prenda
        )
        
        algoritmo = "Random Forest"
        if hasattr(predictor, "metrics") and isinstance(predictor.metrics, dict):
            algoritmo = predictor.metrics.get("algoritmo", "Random Forest")
            
        return PredictionResponse(
            tiempo_estimado_horas=tiempo,
            margen_error_horas=error,
            modelo_version="random_forest_v1",
            prenda_nueva=prenda_nueva,
            algoritmo_usado=algoritmo,
            fuera_de_rango=fuera_de_rango
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/predict/order-items", response_model=OrderPredictionResponse)
def predecir_tiempo_orden_items(
    request: OrderPredictionRequest,
    current_user: Usuario = Depends(get_current_active_user)
):
    """Estima el tiempo de entrega consolidado para múltiples prendas (orden multilínea)"""
    try:
        detalles = []
        prenda_nueva_global = False
        tiempo_total = 0.0
        error_total = 0.0
        
        for item in request.items:
            tiempo, error, prenda_nueva, fuera_de_rango = predictor.predict(
                cantidad_piezas=item.cantidad_piezas,
                prioridad_alta=request.prioridad_alta,
                lineas_produccion=request.lineas_produccion,
                tipo_prenda=item.tipo_prenda
            )
            
            detalles.append(ItemPredictionDetail(
                tipo_prenda=item.tipo_prenda,
                cantidad_piezas=item.cantidad_piezas,
                tiempo_estimado_horas=tiempo,
                margen_error_horas=error,
                prenda_nueva=prenda_nueva,
                fuera_de_rango=fuera_de_rango
            ))
            
            if prenda_nueva:
                prenda_nueva_global = True
            
            if not prenda_nueva_global and tiempo is not None and error is not None:
                tiempo_total += tiempo
                error_total += error
                
        if prenda_nueva_global:
            return OrderPredictionResponse(
                tiempo_estimado_total_horas=None,
                margen_error_total_horas=None,
                prenda_nueva_global=True,
                detalles=detalles
            )
        else:
            return OrderPredictionResponse(
                tiempo_estimado_total_horas=round(tiempo_total, 2),
                margen_error_total_horas=round(error_total, 2),
                prenda_nueva_global=False,
                detalles=detalles
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/prendas-unicas")
def obtener_prendas_unicas(db: Session = Depends(get_session)):
    """Obtiene la lista de prendas (producto_tipo) conocidas por la IA o registradas en BD"""
    try:
        prendas = []
        # Prioridad 1: Obtener prendas directamente de lo que aprendió la red neuronal
        if predictor.model is not None and predictor.features:
            for feature in predictor.features:
                if feature.startswith("tipo_prenda_"):
                    prendas.append(feature.replace("tipo_prenda_", ""))
        else:
            # Fallback: Se obtienen los valores únicos si no hay modelo entrenado
            result = db.execute(text("SELECT DISTINCT producto_tipo FROM linea_orden WHERE producto_tipo IS NOT NULL"))
            prendas = [row[0] for row in result.fetchall()]
            
        # Formatear: capitalizar la primera letra y ordenar alfabéticamente
        prendas_formateadas = sorted([str(p).capitalize() for p in prendas])
        return {"prendas": prendas_formateadas}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/predict/order/{order_id}", response_model=OrderPredictionResponse)
def predecir_tiempo_orden_id(
    order_id: uuid.UUID,
    lineas_produccion: int = 1,
    db: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Estima el tiempo de entrega consolidado para una orden existente en la BD por su ID"""
    try:
        from app.db.orden_model import Orden as OrdenDB
        db_orden = db.get(OrdenDB, order_id)
        if not db_orden:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
            
        prioridad_alta = False
        if db_orden.prioridad and str(db_orden.prioridad).lower() in ["alta", "urgente"]:
            prioridad_alta = True
            
        detalles = []
        prenda_nueva_global = False
        tiempo_total = 0.0
        error_total = 0.0
        
        # Iterar sobre las líneas de la orden
        for linea in db_orden.lineas:
            prenda = linea.producto_tipo or "desconocido"
            cantidad = linea.cantidad or 0
            if cantidad <= 0:
                continue
                
            tiempo, error, prenda_nueva, fuera_de_rango = predictor.predict(
                cantidad_piezas=cantidad,
                prioridad_alta=prioridad_alta,
                lineas_produccion=lineas_produccion,
                tipo_prenda=prenda
            )
            
            detalles.append(ItemPredictionDetail(
                tipo_prenda=prenda,
                cantidad_piezas=cantidad,
                tiempo_estimado_horas=tiempo,
                margen_error_horas=error,
                prenda_nueva=prenda_nueva,
                fuera_de_rango=fuera_de_rango
            ))
            
            if prenda_nueva:
                prenda_nueva_global = True
            
            if not prenda_nueva_global and tiempo is not None and error is not None:
                tiempo_total += tiempo
                error_total += error
                
        if prenda_nueva_global:
            return OrderPredictionResponse(
                tiempo_estimado_total_horas=None,
                margen_error_total_horas=None,
                prenda_nueva_global=True,
                detalles=detalles
            )
        else:
            return OrderPredictionResponse(
                tiempo_estimado_total_horas=round(tiempo_total, 2),
                margen_error_total_horas=round(error_total, 2),
                prenda_nueva_global=False,
                detalles=detalles
            )
    except HTTPException as he:
        raise he
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/projections")
def obtener_proyecciones(current_user: Usuario = Depends(get_current_active_user)):
    """Retorna las proyecciones semanales y mensuales de producción (RF13)"""
    try:
        return predictor.get_projections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bottlenecks")
def obtener_cuellos_de_botella(current_user: Usuario = Depends(get_current_active_user)):
    """Retorna los cuellos de botella y sugerencias de balanceo (RF15)"""
    try:
        return predictor.detect_bottlenecks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active-delays")
def obtener_retrasos_activos(current_user: Usuario = Depends(get_current_active_user)):
    """Detecta tempranamente retrasos en cola activa usando el oráculo IA (RF14)"""
    try:
        return predictor.detect_active_delays()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulate-mts", response_model=List[MtsSimulationItem])
def simular_impacto_mts(
    request: MtsSimulationRequest,
    current_user: Usuario = Depends(get_current_active_user)
):
    """Simula el impacto de un pedido MTS sobre la cola MTO activa (RF16)"""
    try:
        simulacion = predictor.simulate_mts_impact(request.cantidad_piezas)
        return [MtsSimulationItem(**item) for item in simulacion]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/train", response_model=TrainResponse)
def ejecutar_reentrenamiento(current_user: Usuario = Depends(get_current_active_user)):
    """Ejecuta el entrenamiento del modelo. Solo permitido a perfiles Administrador (RF19/RNF-02)"""
    if current_user.rol != Rol.Administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Solo administradores pueden gestionar el modelo de IA."
        )
    try:
        result = train_model()
        return TrainResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del pipeline de entrenamiento: {e}")

@router.post("/upload-train-data", response_model=TrainResponse)
async def subir_datos_entrenamiento(
    file: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Sube un archivo Excel histórico de producción para poblar la BD y entrenar el modelo (Administrador)."""
    if current_user.rol != Rol.Administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Solo administradores pueden subir datos e iniciar el entrenamiento."
        )
    
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de archivo inválido. Debe ser un archivo Excel (.xlsx o .xls)."
        )
        
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Eliminar espacios alrededor de los nombres de columnas
        df.columns = df.columns.str.strip()
        
        required_cols = [
            "Fecha", "Número de Orden", "Cliente", "Tipo", "Prioridad", 
            "Tarea", "Operario", "Máquina", "Prenda", "Piezas Requeridas", 
            "Piezas Buenas", "Piezas Defectuosas", "Horas de Costura", "Estado"
        ]
        
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Columna requerida faltante en el archivo Excel: {col}"
                )
                
        with Session(engine) as db:
            # 1. Desvincular llaves foráneas circulares
            db.execute(text("UPDATE maquina SET operario_asignado_id = NULL"))
            db.execute(text("UPDATE operario SET maquina_actual_id = NULL, orden_actual_id = NULL"))
            
            # 2. Limpiar tablas dependientes (de abajo hacia arriba)
            db.execute(text("DELETE FROM reporte_averia"))
            db.execute(text("DELETE FROM reporte_avance"))
            db.execute(text("DELETE FROM asignacion_orden"))
            db.execute(text("DELETE FROM linea_orden_insumo_link"))
            db.execute(text("DELETE FROM linea_orden"))
            
            # 3. Limpiar tablas principales
            db.execute(text("DELETE FROM orden"))
            db.execute(text("DELETE FROM operario"))
            db.execute(text("DELETE FROM usuario WHERE rol = 'Operario'"))
            db.commit()
            
            ordenes_insertadas = {}

            for _, row in df.iterrows():
                num_orden = str(row["Número de Orden"]).strip()
                cliente = str(row["Cliente"]).strip()
                
                # Normalizar tipo (MTO / MTS)
                tipo_op = str(row["Tipo"]).strip().upper()
                if "MTO" not in tipo_op and "MTS" not in tipo_op:
                    tipo_op = "MTO"
                    
                prioridad = str(row["Prioridad"]).strip().lower()
                if prioridad not in ["baja", "normal", "alta", "urgente"]:
                    prioridad = "normal"
                    
                tarea_str = str(row["Tarea"]).strip()
                operario_full = str(row["Operario"]).strip()
                maquina_cod = str(row["Máquina"]).strip().upper()
                prenda = str(row["Prenda"]).strip().lower()
                piezas_req = int(row["Piezas Requeridas"])
                piezas_buenas = int(row["Piezas Buenas"])
                piezas_def = int(row["Piezas Defectuosas"])
                horas = float(row["Horas de Costura"])
                
                # Normalizar estado de la orden
                estado_str = str(row["Estado"]).strip().upper()
                if estado_str not in ["PENDIENTE", "EN_COLA", "EN_PROCESO", "COMPLETADA"]:
                    estado_str = "COMPLETADA"
                
                # Parsear fecha
                try:
                    fecha_val = pd.to_datetime(row["Fecha"]).to_pydatetime()
                except Exception:
                    fecha_val = datetime.now()
                    
                # 1. Asegurar existencia de la Máquina primero para obtener capacidad_por_hora
                maq_tipo = maquina_cod.split("-")[0].upper()
                if maq_tipo == "PLANCHA":
                    maq_tipo = "PLANCHA_DTF"
                maq_row = db.execute(text("SELECT id, capacidad_por_hora FROM maquina WHERE codigo = :cod LIMIT 1"), {"cod": maquina_cod}).fetchone()
                if not maq_row:
                    maq_id = uuid.uuid4()
                    capacidad_hora = 10.0
                    db.execute(text("""
                        INSERT INTO maquina (id, codigo, tipo, nombre, estado, capacidad_por_hora)
                        VALUES (:mid, :cod, :tipo, :nombre, 'OPERATIVA', :cap)
                    """), {"mid": maq_id, "cod": maquina_cod, "tipo": maq_tipo, "nombre": f"Máquina {maquina_cod}", "cap": capacidad_hora})
                else:
                    maq_id, capacidad_hora = maq_row
                    capacidad_hora = float(capacidad_hora or 10.0)

                # 2. Calcular la eficiencia real de este registro del Excel
                eficiencia_calc = calcular_eficiencia_sesion(piezas_buenas, horas, capacidad_hora)

                # 3. Asegurar la existencia del Operario
                partes = operario_full.split(" ", 1)
                nombre_op = partes[0]
                apellido_op = partes[1] if len(partes) > 1 else ""
                
                op_id = db.execute(text("""
                    SELECT id FROM usuario 
                    WHERE nombre = :nombre AND apellido = :apellido AND rol = 'Operario' 
                    LIMIT 1
                """), {"nombre": nombre_op, "apellido": apellido_op}).scalar()
                
                if not op_id:
                    op_id = uuid.uuid4()
                    correo_fake = f"{nombre_op.lower()}{random.randint(100, 999)}@memefabrica.com"
                    from app.core.security import hash_password
                    pwd_hash = hash_password("Meme2026!")
                    db.execute(text("""
                        INSERT INTO usuario (id, nombre, apellido, correo, hashed_password, rol, estado, debe_cambiar_password)
                        VALUES (:uid, :nombre, :apellido, :correo, :pwd, 'Operario', 'ACTIVO', TRUE)
                    """), {"uid": op_id, "nombre": nombre_op, "apellido": apellido_op, "correo": correo_fake, "pwd": pwd_hash})
                    
                    db.execute(text("""
                        INSERT INTO operario (id, habilidades)
                        VALUES (:opid, :habs)
                    """), {
                        "opid": op_id, 
                        "habs": json.dumps([{"maquina": maq_tipo, "nivel_eficiencia": eficiencia_calc}])
                    })
                else:
                    # Si el operario ya existía, actualizar dinámicamente su eficiencia con este nuevo registro
                    actualizar_eficiencia_operario(db, op_id, maq_tipo, eficiencia_calc)
                
                # 3. Insertar Orden y LineaOrden (solo la primera vez que se ve el Número de Orden)
                if num_orden not in ordenes_insertadas:
                    ord_id = uuid.uuid4()
                    db.execute(text("""
                        INSERT INTO orden (id, numero, cliente, tipo, prioridad, fecha_entrega_estimada, estado, notas, fecha_creacion)
                        VALUES (:oid, :num, :cliente, :tipo, :prio, :fecha, :estado, 'Cargado desde Excel', :fecha)
                    """), {
                        "oid": ord_id,
                        "num": num_orden,
                        "cliente": cliente,
                        "tipo": tipo_op,
                        "prio": prioridad,
                        "fecha": fecha_val,
                        "estado": estado_str
                    })
                    
                    linea_id = uuid.uuid4()
                    db.execute(text("""
                        INSERT INTO linea_orden (id, producto_tipo, descripcion, cantidad, cantidad_completada, talla, color, orden_id)
                        VALUES (:lid, :prenda, :desc, :cant, :cant, 'MIXTA', 'Normal', :oid)
                    """), {
                        "lid": linea_id,
                        "prenda": prenda,
                        "desc": f"Prenda {prenda} cargada desde Excel",
                        "cant": piezas_req,
                        "oid": ord_id
                    })
                    
                    ordenes_insertadas[num_orden] = ord_id
                else:
                    ord_id = ordenes_insertadas[num_orden]
                
                # 4. Insertar Asignación (1 por cada fila de Excel = 1 Tarea)
                asig_id = uuid.uuid4()
                db.execute(text("""
                    INSERT INTO asignacion_orden (id, orden_id, operario_id, tarea, piezas_requeridas, piezas_completadas, estado, fecha_asignacion, notas)
                    VALUES (:aid, :oid, :opid, :tarea, :cant, :cant, 'COMPLETADA', :fecha, 'Cargado desde Excel')
                """), {
                    "aid": asig_id,
                    "oid": ord_id,
                    "opid": op_id,
                    "tarea": tarea_str,
                    "cant": piezas_req,
                    "fecha": fecha_val
                })
                
                # 7. Insertar Reporte de Avance
                rep_id = uuid.uuid4()
                fecha_fin = fecha_val + timedelta(hours=horas)
                db.execute(text("""
                    INSERT INTO reporte_avance (id, asignacion_id, operario_id, piezas_reportadas, piezas_buenas, piezas_defectuosas, estado, fecha_reporte, fecha_validacion, notas, maquina_id)
                    VALUES (:rid, :aid, :opid, :cant, :buenas, :def, 'validado', :fecha_fin, :fecha_fin, 'Cargado desde Excel', :maq_id)
                """), {
                    "rid": rep_id,
                    "aid": asig_id,
                    "opid": op_id,
                    "cant": piezas_req,
                    "buenas": piezas_buenas,
                    "def": piezas_def,
                    "fecha_fin": fecha_fin,
                    "maq_id": str(maq_id)
                })
            
            db.commit()
            
        # Ejecutar reentrenamiento automático usando los nuevos datos de la base de datos
        result_train = train_model()
        return TrainResponse(**result_train)
        
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar archivo: {e}")

@router.post("/seed", response_model=SeedResponse)
def sembrar_datos_historicos(current_user: Usuario = Depends(get_current_active_user)):
    """Siembre datos artificiales en la BD para probar la IA"""
    if current_user.rol != Rol.Administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden sembrar datos de prueba."
        )

    with Session(engine) as db:
        try:
            # 1. Asegurar la existencia de un operario
            op_id = db.execute(text("SELECT id FROM operario LIMIT 1")).scalar()
            if not op_id:
                # Buscar un usuario operario
                user_id = db.execute(text("SELECT id FROM usuario WHERE rol = 'Operario' LIMIT 1")).scalar()
                if not user_id:
                    user_id = uuid.uuid4()
                    # Insertar usuario
                    db.execute(text("""
                        INSERT INTO usuario (id, nombre, apellido, correo, hashed_password, rol, estado)
                        VALUES (:uid, 'Ramon', 'Perez', 'operario1@meme.com', '$2b$12$Z16Hw/pS8J2Tj0G8Qh...fake', 'Operario', 'ACTIVO')
                    """), {"uid": user_id})
                
                op_id = user_id
                db.execute(text("""
                    INSERT INTO operario (id, habilidades)
                    VALUES (:opid, '[{"maquina": "MERROW", "nivel_eficiencia": 88}]')
                """), {"opid": op_id})
            
            # 2. Asegurar máquina operativa
            maq_id = db.execute(text("SELECT id FROM maquina LIMIT 1")).scalar()
            if not maq_id:
                maq_id = uuid.uuid4()
                db.execute(text("""
                    INSERT INTO maquina (id, codigo, tipo, nombre, estado, capacidad_por_hora)
                    VALUES (:mid, 'MERROW-01', 'MERROW', 'Cortadora Merrow', 'OPERATIVA', 10.0)
                """), {"mid": maq_id})

            # 3. Limpiar datos de seed anteriores para evitar duplicados
            db.execute(text("DELETE FROM reporte_avance WHERE notas = 'Carga Seed'"))
            db.execute(text("DELETE FROM asignacion_orden WHERE notas = 'Carga Seed'"))
            db.execute(text("DELETE FROM linea_orden WHERE orden_id IN (SELECT id FROM orden WHERE notas = 'Carga Seed')"))
            db.execute(text("DELETE FROM orden WHERE notas = 'Carga Seed'"))

            # 4. Insertar 25 órdenes y asignaciones completadas distribuidas en 25 días distintos en el pasado
            count = 0
            for i in range(1, 26):
                ord_id = uuid.uuid4()
                asig_id = uuid.uuid4()
                rep_id = uuid.uuid4()
                
                prioridad = random.choice(["baja", "normal", "alta", "urgente"])
                piezas = random.randint(100, 1000)
                interval_str = f"{30 - i} days"
                horas_tomadas = random.uniform(2.0, 10.0)
                
                # Orden
                db.execute(text(f"""
                    INSERT INTO orden (id, numero, cliente, tipo, prioridad, fecha_entrega_estimada, estado, notas, fecha_creacion)
                    VALUES (:oid, :num, 'Cliente de Prueba', 'MTO', :prio, CURRENT_TIMESTAMP, 'COMPLETADA', 'Carga Seed', CURRENT_TIMESTAMP - INTERVAL '{interval_str}')
                """), {
                    "oid": ord_id,
                    "num": f"ORD-SEED-{1000+i}",
                    "prio": prioridad
                })

                # Linea de Orden (cada orden debe tener al menos 1 línea de producto)
                linea_id = uuid.uuid4()
                db.execute(text("""
                    INSERT INTO linea_orden (id, producto_tipo, descripcion, cantidad, cantidad_completada, talla, color, orden_id)
                    VALUES (:lid, 'camiseta', 'Camiseta de Prueba de Seed', :cant, :cant, 'MIXTA', 'Azul', :oid)
                """), {
                    "lid": linea_id,
                    "cant": piezas,
                    "oid": ord_id
                })
                
                # Asignación
                db.execute(text(f"""
                    INSERT INTO asignacion_orden (id, orden_id, operario_id, tarea, piezas_requeridas, piezas_completadas, estado, fecha_asignacion, notas)
                    VALUES (:aid, :oid, :opid, 'Costura General', :cant, :cant, 'COMPLETADA', CURRENT_TIMESTAMP - INTERVAL '{interval_str}', 'Carga Seed')
                """), {
                    "aid": asig_id,
                    "oid": ord_id,
                    "opid": op_id,
                    "cant": piezas
                })
                
                # Reporte de avance
                db.execute(text(f"""
                    INSERT INTO reporte_avance (id, asignacion_id, operario_id, piezas_reportadas, piezas_buenas, piezas_defectuosas, estado, fecha_reporte, fecha_validacion, notas)
                    VALUES (:rid, :aid, :opid, :cant, :cant, 0, 'validado', CURRENT_TIMESTAMP - INTERVAL '{interval_str}' + INTERVAL '{int(horas_tomadas)} hours', CURRENT_TIMESTAMP - INTERVAL '{interval_str}' + INTERVAL '{int(horas_tomadas)} hours', 'Carga Seed')
                """), {
                    "rid": rep_id,
                    "aid": asig_id,
                    "opid": op_id,
                    "cant": piezas
                })
                count += 1
                
            db.commit()
            
            return SeedResponse(
                estado="exitoso",
                mensaje="Registros históricos de producción sembrados con éxito (25 días). Modelo no entrenado automáticamente.",
                registros_insertados=count
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Fallo al sembrar datos: {e}")

@router.get("/status")
def obtener_estado_modelo(current_user: Usuario = Depends(get_current_active_user)):
    """Retorna el estado de calibración y metadatos del modelo (algoritmo, MAE, etc.)"""
    try:
        modelo_cargado = predictor.model is not None
        metricas = getattr(predictor, "metrics", {})
        
        return {
            "modelo_cargado": modelo_cargado,
            "algoritmo_activo": metricas.get("algoritmo", "Ninguno" if not modelo_cargado else "Random Forest"),
            "mae": metricas.get("mae_nuevo"),
            "mse": metricas.get("mse_nuevo"),
            "registros_entrenados": metricas.get("registros_entrenados", 0),
            "fecha_calibracion": metricas.get("fecha_calibracion"),
            "columnas_entrenamiento": predictor.features
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/export-history")
def exportar_historial_excel(current_user: Usuario = Depends(get_current_active_user)):
    """Genera y descarga un archivo Excel con el historial completo de producción (MTO/MTS)"""
    try:
        query = text("""
            SELECT 
                o.fecha_creacion AS "Fecha",
                o.numero AS "Número de Orden",
                o.cliente AS "Cliente",
                o.tipo AS "Tipo",
                o.prioridad AS "Prioridad",
                (u.nombre || ' ' || u.apellido) AS "Operario",
                COALESCE(maq.codigo, 'SIN-MAQUINA') AS "Máquina",
                COALESCE(lo.producto_tipo, 'desconocido') AS "Prenda",
                ao.piezas_requeridas AS "Piezas Requeridas",
                COALESCE(ra.piezas_buenas, 0) AS "Piezas Buenas",
                COALESCE(ra.piezas_defectuosas, 0) AS "Piezas Defectuosas",
                ROUND(CAST(EXTRACT(EPOCH FROM (ra.fecha_reporte - ao.fecha_asignacion)) / 3600.0 AS numeric), 2) AS "Horas de Costura",
                o.estado AS "Estado"
            FROM asignacion_orden ao
            JOIN orden o ON ao.orden_id = o.id
            LEFT JOIN linea_orden lo ON lo.orden_id = o.id
            JOIN usuario u ON ao.operario_id = u.id
            LEFT JOIN operario op ON u.id = op.id
            LEFT JOIN maquina maq ON op.maquina_actual_id = maq.id
            LEFT JOIN reporte_avance ra ON ra.asignacion_id = ao.id AND ra.estado = 'validado'
            ORDER BY o.fecha_creacion DESC
        """)
        
        with Session(engine) as db:
            result = db.execute(query).fetchall()
            
        # Crear DataFrame
        cols = [
            "Fecha", "Número de Orden", "Cliente", "Tipo", "Prioridad", 
            "Operario", "Máquina", "Prenda", "Piezas Requeridas", 
            "Piezas Buenas", "Piezas Defectuosas", "Horas de Costura", "Estado"
        ]
        
        df = pd.DataFrame(result, columns=cols)
        
        # Formatear fechas
        if not df.empty and "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.strftime('%Y-%m-%d %H:%M:%S')
            
        # Escribir DataFrame a un objeto BytesIO Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Historial Produccion')
            
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=historial_produccion.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Fallo al exportar historial: {e}")
