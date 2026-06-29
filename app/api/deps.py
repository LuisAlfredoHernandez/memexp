from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlmodel import Session
from app.core.config import settings
from app.db.session import get_session
from app.db.usuario_model import Usuario
from app.schemas.token import TokenData
from app.schemas.usuario import UsuarioEstado
import uuid

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_session)
) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(sub=user_id)
    except JWTError:
        raise credentials_exception
    
    try:
        parsed_uuid = uuid.UUID(token_data.sub)
    except ValueError:
        raise credentials_exception

    user = db.get(Usuario, parsed_uuid)
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(
    current_user: Annotated[Usuario, Depends(get_current_user)]
) -> Usuario:
    if current_user.estado != UsuarioEstado.ACTIVO:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    return current_user
