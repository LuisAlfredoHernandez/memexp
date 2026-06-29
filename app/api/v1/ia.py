from fastapi import APIRouter, Depends, HTTPException, status
import urllib.request
import json
from app.api.deps import get_current_active_user
from app.db.usuario_model import Usuario, Rol

router = APIRouter(prefix="/ia", tags=["IA Predictiva"])

ML_SERVICE_URL = "http://ml-api:8000/api/v1"

def call_ml_service(endpoint: str, method: str = "GET", payload: dict = None):
    url = f"{ML_SERVICE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            detail = json.loads(error_body).get("detail", error_body)
        except:
            detail = error_body
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo de conexión con servicio ML interno: {e}")

@router.get("/projections")
def obtener_proyecciones(current_user: Usuario = Depends(get_current_active_user)):
    """Retorna las proyecciones semanales y mensuales de producción (RF13)"""
    return call_ml_service("/predict/projections", "GET")

@router.get("/bottlenecks")
def obtener_cuellos_de_botella(current_user: Usuario = Depends(get_current_active_user)):
    """Retorna los cuellos de botella y sugerencias de balanceo (RF15)"""
    return call_ml_service("/predict/bottlenecks", "GET")

@router.post("/simulate-mts")
def simular_impacto_mts(payload: dict, current_user: Usuario = Depends(get_current_active_user)):
    """Simula el impacto de un pedido MTS sobre la cola MTO activa (RF16)"""
    return call_ml_service("/predict/simulate-mts", "POST", payload)

@router.post("/train")
def ejecutar_reentrenamiento(current_user: Usuario = Depends(get_current_active_user)):
    """Ejecuta el entrenamiento del modelo. Solo permitido a perfiles Administrador (RF19/RNF-02)"""
    if current_user.rol != Rol.Administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Solo administradores pueden gestionar el modelo de IA."
        )
    return call_ml_service("/train", "POST")

@router.post("/seed")
def sembrar_datos_historicos(current_user: Usuario = Depends(get_current_active_user)):
    """Siembre datos artificiales en la BD para probar la IA"""
    if current_user.rol != Rol.Administrador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden sembrar datos de prueba."
        )
    return call_ml_service("/seed-data", "POST")
