from fastapi import APIRouter, HTTPException, status
from app.schemas.insumo import Insumo, InsumoCreate, InsumoUpdate

router = APIRouter(prefix="/insumos", tags=["Inventario - Insumos"])

@router.get("/", response_model=list[Insumo])
async def obtener_insumos():
    return []

@router.get("/{id}", response_model=Insumo)
async def obtener_insumo(id: str):
    return {"id": id, "nombre": "Ejemplo"}

@router.post("/", response_model=Insumo, status_code=status.HTTP_201_CREATED)
async def crear_insumo(insumo: InsumoCreate):
    return {**insumo.model_dump(), "id": "new-uuid"}

@router.patch("/{id}", response_model=Insumo)
async def actualizar_insumo(id: str, insumo: InsumoUpdate):
    return {**insumo.model_dump(), "id": id}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_insumo(id: str):
    return None