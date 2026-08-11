from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import calendar

from app.db.session import get_session
from app.db.reporte_avance_model import ReporteAvance
from app.db.asignacion_model import AsignacionOrden
from app.db.orden_model import Orden
from app.db.maquina_model import Maquina
from app.db.operario_model import Operario
from app.schemas.dashboard import DashboardStatsResponse

router = APIRouter()

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(periodo: str = "semana", session: Session = Depends(get_session)):
    max_date_db = session.query(func.max(func.date(ReporteAvance.fecha_reporte))).scalar()
    hoy = max_date_db if max_date_db else datetime.now(timezone.utc).date()
    if periodo == "mes":
        dias_historia = 29
        dias_multiplicador = 30
    else:
        dias_historia = 6
        dias_multiplicador = 7

    fecha_inicio_periodo = hoy - timedelta(days=dias_historia)
    
    # 1. DATOS PERIODO
    fechas = [hoy - timedelta(days=i) for i in range(dias_historia, -1, -1)]
    datos_semana = []
    
    for d in fechas:
        dia_str = calendar.day_name[d.weekday()][:3].capitalize()
        
        # MTO
        mto_count = session.query(func.sum(ReporteAvance.piezas_buenas)).join(AsignacionOrden).join(Orden).filter(
            func.date(ReporteAvance.fecha_reporte) == d,
            Orden.tipo == "MTO"
        ).scalar() or 0
        
        # MTS
        mts_count = session.query(func.sum(ReporteAvance.piezas_buenas)).join(AsignacionOrden).join(Orden).filter(
            func.date(ReporteAvance.fecha_reporte) == d,
            Orden.tipo == "MTS"
        ).scalar() or 0
        
        real = mto_count + mts_count
        meta = 30
        eficiencia = int((real / meta) * 100) if meta > 0 else 0
        if eficiencia > 100:
            eficiencia = 100
            
        datos_semana.append({
            "d": dia_str,
            "real": int(real),
            "meta": meta,
            "mto": int(mto_count),
            "mts": int(mts_count),
            "eficiencia": eficiencia
        })
        
    # 2. MAQUINAS USO
    maquinas = session.execute(select(Maquina)).scalars().all()
    maquinas_uso = []
    
    for maq in maquinas:
        piezas_periodo = session.query(func.sum(ReporteAvance.piezas_buenas)).filter(
            ReporteAvance.maquina_id == str(maq.id),
            func.date(ReporteAvance.fecha_reporte) >= fecha_inicio_periodo,
            func.date(ReporteAvance.fecha_reporte) <= hoy
        ).scalar() or 0
        
        capacidad_periodo = maq.capacidad_por_hora * 8 * dias_multiplicador
        uso = int((piezas_periodo / capacidad_periodo) * 100) if capacidad_periodo > 0 else 0
        if uso > 100:
            uso = 100
            
        estado_str = maq.estado.value if hasattr(maq.estado, "value") else str(maq.estado)
            
        maquinas_uso.append({
            "codigo": maq.codigo,
            "tipo": maq.tipo,
            "uso": uso,
            "estado": estado_str,
            "piezasSemana": int(piezas_periodo)
        })
        
    # 3. OPERARIOS RENDIMIENTO
    operarios = session.execute(select(Operario)).scalars().all()
    operarios_rend = []
    
    for op in operarios:
        piezas_periodo = session.query(func.sum(ReporteAvance.piezas_buenas)).filter(
            ReporteAvance.operario_id == op.id,
            func.date(ReporteAvance.fecha_reporte) >= fecha_inicio_periodo,
            func.date(ReporteAvance.fecha_reporte) <= hoy
        ).scalar() or 0
        
        meta_op = 30 * dias_multiplicador
        eficiencia = int((piezas_periodo / meta_op) * 100) if meta_op > 0 else 0
        if eficiencia > 100:
            eficiencia = 100
            
        estado_str = op.estado if op.estado else "activo"
        if estado_str == "activo":
            estado_str = "activo"
        
        operarios_rend.append({
            "nombre": f"{op.nombre} {op.apellido[0] + '.' if op.apellido else ''}",
            "eficiencia": eficiencia,
            "piezasSemana": int(piezas_periodo),
            "estado": estado_str
        })
        
    operarios_rend.sort(key=lambda x: x["eficiencia"], reverse=True)

    from sqlalchemy import cast, String
    # 4. DISTRIBUCION MAQUINAS
    # Sumar piezas del periodo agrupado por tipo de máquina
    dist_query = session.query(
        Maquina.tipo, 
        func.sum(ReporteAvance.piezas_buenas)
    ).join(ReporteAvance, cast(ReporteAvance.maquina_id, String) == cast(Maquina.id, String)).filter(
        func.date(ReporteAvance.fecha_reporte) >= fecha_inicio_periodo,
        func.date(ReporteAvance.fecha_reporte) <= hoy
    ).group_by(Maquina.tipo).all()

    color_map = {
        "plana": "#f97316", # orange
        "corte": "#10b981", # emerald
        "merrow": "#0ea5e9", # sky
        "cover": "#8b5cf6", # violet
        "plancha_dtf": "#ef4444" # red
    }
    
    distribucion_maquinas = []
    for tipo, total in dist_query:
        if total > 0:
            if hasattr(tipo, "value"):
                tipo_str = tipo.value
            elif hasattr(tipo, "name"):
                tipo_str = tipo.name.lower()
            else:
                tipo_str = str(tipo).split(".")[-1].lower()
                
            distribucion_maquinas.append({
                "nombre": tipo_str.capitalize(),
                "valor": int(total),
                "color": color_map.get(tipo_str, "#94a3b8")
            })
            
    return {
        "datos_semana": datos_semana,
        "maquinas_uso": maquinas_uso,
        "operarios_rendimiento": operarios_rend,
        "distribucion_maquinas": distribucion_maquinas
    }
