from sqlmodel import create_engine, Session, SQLModel
from app.core.config import settings

# El motor de la base de datos se crea usando la URL desde la configuración
engine = create_engine(settings.DATABASE_URL, echo=settings.ECHO_SQL)

def create_db_and_tables():
    """
    Inicializa la base de datos y crea todas las tablas definidas en los modelos.
    NOTA: Esta función es útil para desarrollo y pruebas. En un entorno de producción,
    la gestión de la base de datos debería realizarse a través de un sistema de migraciones
    como Alembic para manejar los cambios de esquema de forma controlada.
    """
    SQLModel.metadata.create_all(engine)

    # Sembrar prendas iniciales si no existen
    with Session(engine) as db:
        from app.db.prenda_model import Prenda
        from sqlmodel import select, func
        
        prendas_iniciales = ["Licra deportiva", "Jogger", "Vestido", "T-shirt", "Short", "Blusa"]
        for p_nombre in prendas_iniciales:
            existente = db.exec(select(Prenda).where(func.lower(Prenda.nombre) == func.lower(p_nombre))).first()
            if not existente:
                db.add(Prenda(nombre=p_nombre))
        db.commit()

def get_session():
    """Generador de dependencias para la sesión de la base de datos."""
    with Session(engine) as session:
        yield session
