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
def get_dashboard_stats(session: Session = Depends(get_session)):
    max_date_db = session.query(func.max(func.date(ReporteAvance.fecha_reporte))).scalar()
    hoy = max_date_db if max_date_db else datetime.now(timezone.utc).date()
    
    # 1. DATOS SEMANA (Últimos 7 días)
    fechas = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
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
        piezas_hoy = session.query(func.sum(ReporteAvance.piezas_buenas)).filter(
            ReporteAvance.maquina_id == str(maq.id),
            func.date(ReporteAvance.fecha_reporte) == hoy
        ).scalar() or 0
        
        capacidad_dia = maq.capacidad_por_hora * 8
        uso = int((piezas_hoy / capacidad_dia) * 100) if capacidad_dia > 0 else 0
        if uso > 100:
            uso = 100
            
        estado_str = maq.estado.value if hasattr(maq.estado, "value") else str(maq.estado)
            
        maquinas_uso.append({
            "codigo": maq.codigo,
            "tipo": maq.tipo,
            "uso": uso,
            "estado": estado_str,
            "piezasHoy": int(piezas_hoy)
        })
        
    # 3. OPERARIOS RENDIMIENTO
    operarios = session.execute(select(Operario)).scalars().all()
    operarios_rend = []
    
    for op in operarios:
        piezas_hoy = session.query(func.sum(ReporteAvance.piezas_buenas)).filter(
            ReporteAvance.operario_id == op.id,
            func.date(ReporteAvance.fecha_reporte) == hoy
        ).scalar() or 0
        
        meta_op = 30
        eficiencia = int((piezas_hoy / meta_op) * 100) if meta_op > 0 else 0
        if eficiencia > 100:
            eficiencia = 100
            
        estado_str = op.estado if op.estado else "activo"
        if estado_str == "activo":
            estado_str = "activo"
        
        operarios_rend.append({
            "nombre": f"{op.nombre} {op.apellido[0] + '.' if op.apellido else ''}",
            "eficiencia": eficiencia,
            "piezasHoy": int(piezas_hoy),
            "estado": estado_str
        })

    from sqlalchemy import cast, String
    # 4. DISTRIBUCION MAQUINAS
    # Sumar piezas de hoy agrupado por tipo de máquina
    dist_query = session.query(
        Maquina.tipo, 
        func.sum(ReporteAvance.piezas_buenas)
    ).join(ReporteAvance, cast(ReporteAvance.maquina_id, String) == cast(Maquina.id, String)).filter(
        func.date(ReporteAvance.fecha_reporte) == hoy
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
        if total and total > 0:
            color = color_map.get(str(tipo).lower(), "#64748b")
            distribucion_maquinas.append({
                "nombre": str(tipo).capitalize(),
                "valor": int(total),
                "color": color
            })
            
    return {
        "datos_semana": datos_semana,
        "maquinas_uso": maquinas_uso,
        "operarios_rendimiento": operarios_rend,
        "distribucion_maquinas": distribucion_maquinas
    }
