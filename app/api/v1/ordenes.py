from fastapi import APIRouter, HTTPException, status
from app.schemas.orden import Orden, OrdenBase

router = APIRouter(prefix="/ordenes", tags=["Producción - Órdenes"])

@router.get("/", response_model=list[Orden])
async def listar_ordenes():
    return []

@router.post("/", response_model=Orden, status_code=status.HTTP_201_CREATED)
async def crear_orden(orden: OrdenBase):
    return {**orden.model_dump(), "id": "ord-uuid", "fecha_creacion": "2024-01-01T00:00:00"}

@router.get("/{id}", response_model=Orden)
async def obtener_orden(id: str):
    return {"id": id, "numero": "OP-100"}

@router.patch("/{id}", response_model=Orden)
async def actualizar_orden(id: str, orden: OrdenBase):
    return {**orden.model_dump(), "id": id}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_orden(id: str):
    return None