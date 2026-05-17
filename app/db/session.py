from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# El motor de la base de datos se crea usando la URL desde la configuración
engine = create_engine(settings.DATABASE_URL, echo=True)

def create_db_and_tables():
    """
    Inicializa la base de datos y crea todas las tablas definidas en los modelos.
    SQLModel necesita que los modelos sean importados en algún punto para conocerlos.
    El __init__.py de la carpeta db ya se encarga de esto.
    """
    SQLModel.metadata.create_all(engine)

def get_session():
    """Generador de dependencias para la sesión de la base de datos."""
    with Session(engine) as session:
        yield session
