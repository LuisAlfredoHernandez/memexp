import uuid
import json
from sqlmodel import Session
from app.db.operario_model import Operario

def clean_maquina_tipo(val) -> str:
    """Sanea el tipo de máquina eliminando prefijos de Enum como 'maquinatipo.merrow' -> 'merrow'."""
    if hasattr(val, "value"):
        val = val.value
    s = str(val).strip().lower()
    if "." in s:
        s = s.split(".")[-1]
    return s

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
    alpha_min: float = 0.10,
    alpha_max: float = 1.0
) -> None:
    """
    Actualiza el nivel de eficiencia de un operario para una máquina usando
    Media Móvil Ponderada Exponencial (EWMA) con Alpha dinámico.
    Nuevo Nivel = alpha_efectivo * Eficiencia Sesión + (1 - alpha_efectivo) * Nivel Previo
    """
    db_operario = db.get(Operario, operario_id)
    if not db_operario:
        return

    maquina_tipo_clean = clean_maquina_tipo(maquina_tipo)

    # Cargar lista actual de habilidades
    habilidades = db_operario.habilidades or []
    if isinstance(habilidades, str):
        try:
            habilidades = json.loads(habilidades)
        except Exception:
            habilidades = []

    # Convertir elementos y sanear tipos de máquina
    habilidades_list = []
    for item in habilidades:
        if isinstance(item, dict):
            h_dict = dict(item)
        elif hasattr(item, "model_dump"):
            h_dict = item.model_dump()
        elif hasattr(item, "dict"):
            h_dict = item.dict()
        else:
            continue
        
        h_dict["maquina"] = clean_maquina_tipo(h_dict.get("maquina", ""))
        habilidades_list.append(h_dict)

    # Buscar la habilidad correspondiente a esta máquina
    habilidad_existente = None
    for h in habilidades_list:
        if h.get("maquina") == maquina_tipo_clean:
            habilidad_existente = h
            break

    eficiencia_sesion_int = min(100, max(0, int(round(eficiencia_sesion))))

    if habilidad_existente:
        nivel_previo = habilidad_existente.get("nivel_eficiencia", 0)
        sesiones_historicas = habilidad_existente.get("sesiones", 1)
        
        # Incrementar historial de sesiones
        sesiones_historicas += 1
        habilidad_existente["sesiones"] = sesiones_historicas
        
        # Alpha dinámico basado en historial de sesiones: 2 / (N + 1)
        alpha_calculado = 2.0 / (sesiones_historicas + 1)
        alpha_efectivo = max(alpha_min, min(alpha_max, alpha_calculado))
        
        nuevo_nivel = round((alpha_efectivo * eficiencia_sesion_int) + ((1.0 - alpha_efectivo) * nivel_previo))
        habilidad_existente["nivel_eficiencia"] = min(100, max(0, int(nuevo_nivel)))
    else:
        habilidades_list.append({
            "maquina": maquina_tipo_clean,
            "nivel_eficiencia": eficiencia_sesion_int,
            "sesiones": 1
        })

    db_operario.habilidades = habilidades_list
    db.add(db_operario)
    db.commit()
    db.refresh(db_operario)
