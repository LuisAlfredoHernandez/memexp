import os
from sqlmodel import Session, create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://memexp_user:memexp_password@db:5432/memexp_db")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    result = session.exec(text("""
        SELECT r.id, r.maquina_id, r.notas, r.piezas_reportadas, r.estado 
        FROM reporte_avance r 
        JOIN operario o ON r.operario_id = o.id 
        JOIN usuario u ON o.id = u.id 
        WHERE u.nombre = 'Ramiro'
    """)).all()
    
    for row in result:
        print(f"Reporte: {row[0]}, maquina_id: {row[1]}, notas: {row[2]}, p.rep: {row[3]}, estado: {row[4]}")
