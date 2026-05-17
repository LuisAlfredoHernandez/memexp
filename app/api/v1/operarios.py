from fastapi import APIRouter, status
from app.schemas.operario import Operario, OperarioCreate, OperarioUpdate

router = APIRouter(prefix="/operarios", tags=["Planta - Operarios"])

@router.get("/", response_model=list[Operario])
async def listar_operarios():
    return []

@router.post("/", response_model=Operario, status_code=status.HTTP_201_CREATED)
async def crear_operario(operario: OperarioCreate):
    operario_data = operario.model_dump(exclude={"password"})
    return {**operario_data, "id": "op-uuid-new"}

@router.get("/{id}", response_model=Operario)
async def obtener_operario(id: str):
    return {"id": id, "nombre": "Gema", "apellido": "Ini", "correo": "gema.op@example.com", "rol": "operario", "estado": "activo", "habilidades": []}

@router.patch("/{id}", response_model=Operario)
async def actualizar_operario(id: str, operario: OperarioUpdate):
    update_data = operario.model_dump(exclude_unset=True)
    return {"id": id, "nombre": "Gema", "apellido": "Ini", "correo": "gema.op@example.com", "rol": "operario", "estado": "activo", "habilidades": [], **update_data}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_operario(id: str):
    return None