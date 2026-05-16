import uuid
from sqlmodel import Field, SQLModel

class Usuario(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nombre: str
    apellido: str
    correo: str = Field(unique=True, index=True)
    rol: str
    estado: str
    hashed_password: str
