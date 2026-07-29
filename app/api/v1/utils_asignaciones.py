from sqlmodel import Session, select
from app.db.asignacion_model import AsignacionOrden
from app.db.operario_model import Operario
from app.db.maquina_model import Maquina
import uuid

def revisar_y_liberar_maquina(db: Session, operario_id: uuid.UUID):
    """
    Revisa si el operario tiene órdenes en proceso o pendientes.
    Si no tiene ninguna, libera la máquina actual del operario 
    y desasigna al operario de la máquina.
    """
    operario = db.get(Operario, operario_id)
    if not operario or not operario.maquina_actual_id:
        return
        
    tiene_pendientes = db.exec(
        select(AsignacionOrden)
        .where(AsignacionOrden.operario_id == operario_id)
        .where(AsignacionOrden.estado.in_(["en_proceso", "pendiente"]))
    ).first() is not None
    
    if not tiene_pendientes:
        maquina_id = operario.maquina_actual_id
        
        # Desasignar del operario
        operario.maquina_actual_id = None
        db.add(operario)
        
        # Desasignar de la máquina
        maquina = db.get(Maquina, maquina_id)
        if maquina and maquina.operario_asignado_id == operario_id:
            maquina.operario_asignado_id = None
            db.add(maquina)
