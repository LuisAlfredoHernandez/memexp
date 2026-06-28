from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from app.api.v1 import auth, insumos, operarios, maquinas, ordenes, usuarios, asignaciones, reportes_avance, reportes_averia
from app.db.session import create_db_and_tables
from app.core.websocket import manager

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

@app.websocket("/ws/updates")
async def websocket_updates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantener el socket abierto y responder a pings/mensajes si aplica
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Inclusión de routers
app.include_router(auth.router)
app.include_router(insumos.router)
app.include_router(operarios.router)
app.include_router(maquinas.router)
app.include_router(ordenes.router)
app.include_router(usuarios.router)
app.include_router(asignaciones.router)
app.include_router(reportes_avance.router)
app.include_router(reportes_averia.router)


@app.get("/")
async def root():
    return {"message": "Bienvenido al Sistema de Gestión de Meme Fábricas"}