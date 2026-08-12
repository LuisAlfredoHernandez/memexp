from sqlmodel import Session, select, create_engine
from app.db.usuario_model import Usuario
import os

engine = create_engine("postgresql://memexp_user:memexp_password@localhost:5432/memexp_db")

with Session(engine) as session:
    users = session.exec(select(Usuario)).all()
    for u in users:
        print(f"ID: {u.id}, Correo: {u.correo}, Rol: {u.rol}, Nombre: {u.nombre}, Apellido: {u.apellido}, Estado: {u.estado}")
