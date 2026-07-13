from typing import Optional
import uuid
from sqlmodel import SQLModel, Field

class Prenda(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    nombre: str = Field(index=True, unique=True)
