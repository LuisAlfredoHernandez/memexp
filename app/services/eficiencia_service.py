import uuid
import json
from sqlmodel import Session
from app.db.operario_model import Operario

def calcular_eficiencia_sesion(piezas_buenas: int, horas_trabajadas: float, capacidad_por_hora: float) -> int:
    """
    Calcula el porcentaje de eficiencia para una sesión o turno específico.
    Fórmula: ( (Piezas Buenas / Horas) / Capacidad_Por_Hora ) * 100
    Si los datos no son válidos (horas <= 0 o capacidad <= 0), retorna 0 por defecto.
    """
    if horas_trabajadas <= 0 or capacidad_por_hora <= 0 or piezas_buenas < 0:
        return 0
    
    velocidad_real = piezas_buenas / horas_trabajadas
    eficiencia = (velocidad_real / capacidad_por_hora) * 100.0
    return min(100, max(0, int(round(eficiencia))))


def actualizar_eficiencia_operario(
    db: Session,
    operario_id: uuid.UUID,
    maquina_tipo: str,
    eficiencia_sesion: float,
    alpha: float = 0.20
) -> None:
    """
    Actualiza el nivel de eficiencia de un operario para una máquina usando
    Media Móvil Ponderada Exponencial (EWMA):
    Nuevo Nivel = alpha * Eficiencia Sesión + (1 - alpha) * Nivel Previo
    """
    db_operario = db.get(Operario, operario_id)
    if not db_operario:
        return

    maquina_tipo_clean = str(maquina_tipo).strip().lower()

    # Cargar lista actual de habilidades
    habilidades = db_operario.habilidades or []
    if isinstance(habilidades, str):
        try:
            habilidades = json.loads(habilidades)
        except Exception:
            habilidades = []

    # Convertir elementos de Pydantic a dict si fuera necesario
    habilidades_list = []
    for item in habilidades:
        if isinstance(item, dict):
            habilidades_list.append(dict(item))
        elif hasattr(item, "model_dump"):
            habilidades_list.append(item.model_dump())
        elif hasattr(item, "dict"):
            habilidades_list.append(item.dict())

    # Buscar la habilidad correspondiente a esta máquina
    habilidad_existente = None
    for h in habilidades_list:
        if str(h.get("maquina", "")).strip().lower() == maquina_tipo_clean:
            habilidad_existente = h
            break

    eficiencia_sesion_int = min(100, max(0, int(round(eficiencia_sesion))))

    if habilidad_existente:
        nivel_previo = habilidad_existente.get("nivel_eficiencia", 0)
        nuevo_nivel = round((alpha * eficiencia_sesion_int) + ((1.0 - alpha) * nivel_previo))
        habilidad_existente["nivel_eficiencia"] = min(100, max(0, int(nuevo_nivel)))
    else:
        habilidades_list.append({
            "maquina": maquina_tipo_clean,
            "nivel_eficiencia": eficiencia_sesion_int
        })

    db_operario.habilidades = habilidades_list
    db.add(db_operario)
    db.commit()
    db.refresh(db_operario)
