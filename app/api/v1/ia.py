from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import uuid
import random
from sqlalchemy import text
from sqlmodel import Session

from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario, Rol
from app.db.session import engine

# Importar esquemas
from app.schemas.predict import (
    PredictionRequest, PredictionResponse,
    MtsSimulationRequest, MtsSimulationItem,
    TrainResponse, SeedResponse
)

# Importar servicios
from app.services.ml_engine.predictor import predictor
from app.services.ml_engine.pipeline import train_model

router = APIRouter(prefix="/ia", tags=["IA Predictiva"])

@router.post("/predict/delivery-time", response_model=PredictionResponse)
def predecir_tiempo_entrega(
    request: PredictionRequest,
    current_user: Usuario = Depends(get_current_active_user)
):
    """Estima el tiempo de entrega de una asignación en horas (RF12)"""
    try:
        tiempo, error = predictor.predict(
            cantidad_piezas=request.cantidad_piezas,
            prioridad_alta=request.prioridad_alta,
            lineas_produccion=request.lineas_produccion
        )
        return PredictionResponse(
            tiempo_estimado_horas=tiempo,
            margen_error_horas=error,
            modelo_version="random_forest_v1"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
                user_id = db.execute(text("SELECT id FROM usuario WHERE rol = 'operario' LIMIT 1")).scalar()
                if not user_id:
                    user_id = uuid.uuid4()
                    # Insertar usuario
                    db.execute(text("""
                        INSERT INTO usuario (id, nombre, apellido, correo, hashed_password, rol, estado)
                        VALUES (:uid, 'Ramon', 'Perez', 'operario1@meme.com', '$2b$12$Z16Hw/pS8J2Tj0G8Qh...fake', 'operario', 'activo')
                    """), {"uid": user_id})
                
                op_id = user_id
                db.execute(text("""
                    INSERT INTO operario (id, maquinaActual, habilidades, estado)
                    VALUES (:opid, 'merrow-01', '[{"maquina": "merrow", "nivel_eficiencia": 88}]', 'activo')
                """), {"opid": op_id})
            
            # 2. Asegurar máquina operativa
            maq_id = db.execute(text("SELECT id FROM maquina LIMIT 1")).scalar()
            if not maq_id:
                maq_id = uuid.uuid4()
                db.execute(text("""
                    INSERT INTO maquina (id, codigo, tipo, nombre, estado, capacidad_por_hora)
                    VALUES (:mid, 'MERROW-01', 'merrow', 'Cortadora Merrow', 'operativa', 10.0)
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
            
            # Inicializar el primer modelo para que no dé fallback
            try:
                train_model()
            except Exception as e:
                print("Error al calibrar inicial en seed:", e)
                
            return SeedResponse(
                estado="exitoso",
                mensaje="Registros históricos de producción sembrados con éxito (25 días) y modelo calibrado.",
                registros_insertados=count
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Fallo al sembrar datos: {e}")
