from sqlmodel import Field, SQLModel
import uuid

class Insumo(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    nombre: str = Field(unique=True)
    descripcion: str | None = None
    unidad_almacenamiento: str # Ej: 'metros', 'unidades', 'litros'
