from passlib.context import CryptContext

# Se crea una única instancia de CryptContext para ser reutilizada en toda la aplicación.
# Esto es mucho más eficiente que crear una nueva en cada petición.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Genera el hash de una contraseña usando el contexto global."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña plana contra su hash."""
    return pwd_context.verify(plain_password, hashed_password)