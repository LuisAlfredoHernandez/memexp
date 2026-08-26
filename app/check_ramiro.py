import os
from sqlmodel import Session, create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://memexp_user:memexp_password@db:5432/memexp_db")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    result = session.exec(text("""
        SELECT r.id, r.maquina_id, u.nombre, u.apellido, o.maquina_actual_id
        FROM reporte_avance r 
        JOIN operario o ON r.operario_id = o.id 
        JOIN usuario u ON o.id = u.id 
        WHERE u.nombre = 'Ramiro'
    """)).all()
    
    for row in result:
        print(f"Reporte: {row[0]}, maquina_id: {row[1]}, nombre: {row[2]} {row[3]}, maquina_actual_id: {row[4]}")
