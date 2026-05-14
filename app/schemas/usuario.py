from pydantic import BaseModel, EmailStr, Field

class UsuarioBase(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    rol: str
    estado: str

class UsuarioCreate(UsuarioBase):
    password: str = Field(..., min_length=8)

class Usuario(UsuarioBase):
    id: str

    class ConfigDict:
        from_attributes = True

class UsuarioUpdate(UsuarioBase):
    password: str | None = None
    estado: str | None = None
    rol: str | None = None
    correo: EmailStr | None = None
    nombre: str | None = None
    apellido: str | None = None