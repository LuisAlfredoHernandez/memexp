from fastapi import FastAPI
from app.api.v1 import insumos, operarios, maquinas, ordenes, usuarios

app = FastAPI(title="Meme Fábricas API", version="1.0.0")

# Inclusión de routers
app.include_router(insumos.router)
app.include_router(operarios.router)
app.include_router(maquinas.router)
app.include_router(ordenes.router)
app.include_router(usuarios.router)

@app.get("/")
async def root():
    return {"message": "Bienvenido al Sistema de Gestión de Meme Fábricas"}