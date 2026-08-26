import os
from sqlmodel import Session, create_engine, text

# Conectar a la DB. Usamos variables de entorno o el string por defecto.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://memexp_user:memexp_password@db:5432/memexp_db")
engine = create_engine(DATABASE_URL)

with Session(engine) as session:
    real_hash = "$2b$12$6nW2TP12XytQh85IC61rR./Hl1yQ7VXYfEJuNtX4uKjA/V4qrZrWq"
    fake_hash = "$2b$12$Z16Hw/pS8J2Tj0G8Qh...fake"
    
    result = session.exec(text("UPDATE usuario SET hashed_password = :real WHERE hashed_password = :fake"), params={"real": real_hash, "fake": fake_hash})
    session.commit()
    print(f"Filas actualizadas: {result.rowcount}")
