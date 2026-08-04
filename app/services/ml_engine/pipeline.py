import os
import joblib
import pandas as pd
import numpy as np
from sqlalchemy import text
from sqlmodel import Session
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from app.core.config import settings
from app.db.session import engine

def train_model():
    """
    Ejecuta el pipeline de reentrenamiento del modelo utilizando datos reales de la BD.
    Cumple con:
    - RF19 (Reentrenamiento manual)
    - RF20 / RNF-09 (Validar suficiencia de datos flexibilizada a al menos 1 día)
    - RF21 / RNF-10 (Comparar MAE/MSE de manera informativa únicamente)
    """
    with Session(engine) as db:
        # 1. RNF-09: Validar que exista al menos 1 día de registros de producción en la BD
        dias_query = text("""
            SELECT COUNT(DISTINCT DATE(fecha_reporte)) 
            FROM reporte_avance 
            WHERE estado = 'validado'
        """)
        unique_days = db.execute(dias_query).scalar() or 0
        
        if unique_days < 1:
            raise ValueError(
                "Suficiencia de datos inválida: Se requiere al menos 1 día de reportes de avance validados para entrenar el modelo."
            )

        # 2. Consultar histórico de producción (Solo Lectura)
        query = text("""
            SELECT 
                MAX(lo.cantidad) AS cantidad_piezas,
                CASE WHEN LOWER(o.prioridad::text) IN ('alta', 'urgente') THEN 1 ELSE 0 END AS prioridad_alta,
                1 AS lineas_produccion,
                COALESCE(MAX(lo.producto_tipo), 'desconocido') AS tipo_prenda,
                EXTRACT(EPOCH FROM (MAX(ra.fecha_reporte) - MIN(ao.fecha_asignacion))) / 3600.0 AS tiempo_horas
            FROM orden o
            JOIN asignacion_orden ao ON ao.orden_id = o.id
            LEFT JOIN linea_orden lo ON lo.orden_id = o.id
            JOIN reporte_avance ra ON ra.asignacion_id = ao.id
            WHERE o.estado::text = 'COMPLETADA' AND ra.estado = 'validado'
            GROUP BY o.id, o.prioridad
        """)
        
        result = db.execute(query).fetchall()
        
        if len(result) < 2:
            raise ValueError(
                f"Registros insuficientes: Se necesitan al menos 2 órdenes finalizadas "
                f"para calibrar las predicciones (actualmente hay {len(result)})."
            )

        # 3. Modelado con Pandas & Scikit-learn
        df = pd.DataFrame(result, columns=["cantidad_piezas", "prioridad_alta", "lineas_produccion", "tipo_prenda", "tiempo_horas"])
        
        # Saneamiento de datos: eliminar registros con valores corruptos/inválidos
        df = df[(df["tiempo_horas"] > 0) & (df["cantidad_piezas"] > 0)]
        
        if len(df) < 2:
            raise ValueError(
                f"Registros válidos insuficientes tras limpieza: Se necesitan al menos 2 órdenes válidas "
                f"con cantidad y duración mayores a cero (actualmente hay {len(df)})."
            )
        
        # Convertir variables categóricas (tipo_prenda) a numéricas usando One-Hot Encoding
        df_encoded = pd.get_dummies(df, columns=["tipo_prenda"], drop_first=False)
        
        # Las columnas que no son el objetivo "tiempo_horas" son las características
        feature_cols = [c for c in df_encoded.columns if c != "tiempo_horas"]
        
        X = df_encoded[feature_cols]
        y = df_encoded["tiempo_horas"]
        
        # Calcular test_size dinámicamente para evitar conjuntos vacíos en datasets pequeños
        n_samples = len(df)
        if n_samples >= 5:
            test_size = 0.2
        else:
            test_size = 1.0 / n_samples

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

        # Determinar algoritmo según volumen de datos (Modelo Híbrido Dinámico)
        algoritmo_nombre = "Random Forest"
        if n_samples < 10:
            algoritmo_nombre = "Linear Regression"
            new_model = LinearRegression()
        else:
            new_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
            
        new_model.fit(X_train, y_train)

        # Calcular métricas de error
        y_pred = new_model.predict(X_test)
        new_mae = float(mean_absolute_error(y_test, y_pred))
        new_mse = float(mean_squared_error(y_test, y_pred))

        # 4. Comparar con el modelo activo para fines informativos diagnósticos
        active_mae = None
        active_mse = None
        
        if os.path.exists(settings.MODEL_PATH):
            try:
                active_payload = joblib.load(settings.MODEL_PATH)
                if isinstance(active_payload, dict) and "model" in active_payload:
                    active_model = active_payload["model"]
                    active_features = active_payload.get("features", [])
                else:
                    active_model = active_payload
                    active_features = ["cantidad_piezas", "prioridad_alta", "lineas_produccion"]
                
                # Alinear X_test con las características que tenía el modelo activo
                X_test_active = pd.DataFrame(0, index=X_test.index, columns=active_features)
                for col in active_features:
                    if col in X_test.columns:
                        X_test_active[col] = X_test[col]
                
                y_pred_active = active_model.predict(X_test_active)
                active_mae = float(mean_absolute_error(y_test, y_pred_active))
                active_mse = float(mean_squared_error(y_test, y_pred_active))
            except Exception:
                # Si falla al cargar el modelo anterior, ignorar diagnóstico
                pass

        # 5. Guardar modelo y metadatos (Con total fiabilidad, siempre se publica)
        artifacts_dir = os.path.dirname(settings.MODEL_PATH)
        os.makedirs(artifacts_dir, exist_ok=True)
        
        from datetime import datetime
        payload = {
            "model": new_model,
            "features": feature_cols,
            "metrics": {
                "mae_actual": active_mae,
                "mse_actual": active_mse,
                "mae_nuevo": new_mae,
                "mse_nuevo": new_mse,
                "registros_entrenados": len(df),
                "fecha_calibracion": datetime.now().isoformat(),
                "algoritmo": algoritmo_nombre
            }
        }
        joblib.dump(payload, settings.MODEL_PATH)

        return {
            "estado": "exitoso",
            "registros_entrenados": len(df),
            "mae_actual": active_mae,
            "mse_actual": active_mse,
            "mae_nuevo": new_mae,
            "mse_nuevo": new_mse,
            "version_publicada": f"{algoritmo_nombre.lower().replace(' ', '_')}_v1"
        }
