from fastapi import APIRouter, status
from app.schemas.usuario import Usuario, UsuarioCreate, UsuarioUpdate

router = APIRouter(prefix="/usuarios", tags=["Administración - Usuarios"])

@router.get("/", response_model=list[Usuario])
async def listar_usuarios():
    return []

@router.post("/", response_model=Usuario, status_code=status.HTTP_201_CREATED)
async def crear_usuario(usuario: UsuarioCreate):
    user_data = usuario.model_dump(exclude={"password"})
    return {**user_data, "id": "user-uuid"}

@router.get("/{id}", response_model=Usuario)
async def obtener_usuario(id: str):
    return {"id": id, "nombre": "Gema", "apellido": "Ini", "correo": "gema@example.com", "rol": "admin", "estado": "activo"}

@router.patch("/{id}", response_model=Usuario)
async def actualizar_usuario(id: str, usuario: UsuarioUpdate):
    update_data = usuario.model_dump(exclude_unset=True)
    return {"id": id, "nombre": "Gema", "apellido": "Ini", "correo": "gema@example.com", "rol": "admin", "estado": "activo", **update_data}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(id: str):
    return None
