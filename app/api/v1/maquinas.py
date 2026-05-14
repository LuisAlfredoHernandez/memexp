from fastapi import APIRouter, HTTPException, status
from app.schemas.maquina import Maquina

router = APIRouter(prefix="/maquinas", tags=["Planta - Maquinaria"])

@router.get("/", response_model=list[Maquina])
async def listar_maquinas():
    return []

@router.post("/", response_model=Maquina, status_code=status.HTTP_201_CREATED)
async def crear_maquina(maquina: Maquina):
    return {**maquina.model_dump(), "id": "mq-uuid"}

@router.patch("/{id}", response_model=Maquina)
async def actualizar_maquina(id: str, maquina: Maquina):
    return {**maquina.model_dump(), "id": id}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_maquina(id: str):
    return None