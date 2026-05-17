from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.api.v1 import insumos, operarios, maquinas, ordenes, usuarios
from app.db.session import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando aplicación y creando tablas de la base de datos...")
    create_db_and_tables()
    yield
    print("Apagando aplicación.")

app = FastAPI(
    title="Meme Fábricas API",
    version="1.0.0",
    lifespan=lifespan
)

# Inclusión de routers
app.include_router(insumos.router)
app.include_router(operarios.router)
app.include_router(maquinas.router)
app.include_router(ordenes.router)
app.include_router(usuarios.router)

@app.get("/")
async def root():
    return {"message": "Bienvenido al Sistema de Gestión de Meme Fábricas"}