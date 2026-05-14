from fastapi import APIRouter, HTTPException, status
from app.schemas.operario import Operario, OperarioCreate

router = APIRouter(prefix="/operarios", tags=["RRHH - Operarios"])

@router.get("/", response_model=list[Operario])
async def listar_operarios():
    return []

@router.post("/", response_model=Operario, status_code=status.HTTP_201_CREATED)
async def crear_operario(operario: OperarioCreate):
    return {**operario.model_dump(), "id": "op-uuid"}

@router.get("/{id}", response_model=Operario)
async def obtener_operario(id: str):
    return {"id": id, "nombre": "Juan"}

@router.patch("/{id}", response_model=Operario)
async def actualizar_operario(id: str, operario: OperarioCreate):
    return {**operario.model_dump(), "id": id}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_operario(id: str):
    return None