import os
from sqlmodel import Session, create_engine, select
from app.db.maquina_model import Maquina

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://memexp_user:memexp_password@db:5432/memexp_db")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    try:
        maquina_val = "0c0208d4-6aa7-4e95-ab86-c84712f450a9"
        maq_obj = session.exec(select(Maquina).where((Maquina.codigo == maquina_val) | (Maquina.tipo == maquina_val))).first()
        print(f"Éxito: {maq_obj}")
    except Exception as e:
        print(f"Error: {e}")
