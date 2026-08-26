from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from typing import Annotated
from datetime import timedelta
from pydantic import EmailStr
from jose import jwt, JWTError

from app.db.session import get_session
from app.db.usuario_model import Usuario
import uuid
from app.core.security import verify_password, create_access_token, hash_password, create_refresh_token
from app.core.config import settings
from app.schemas.token import Token, PasswordReset, TokenRefreshRequest, PasswordChange
from app.api.deps import get_current_active_user
from app.schemas.usuario import UsuarioEstado
from app.schemas.msg import Msg

router = APIRouter(tags=["Autenticación"])

@router.post("/login", response_model=Token)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_session)
):
    user = db.exec(select(Usuario).where(Usuario.correo == form_data.username)).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.estado == UsuarioEstado.INACTIVO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta de usuario está inactiva",
        )

    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "requires_password_change": user.debe_cambiar_password
    }

@router.post("/password-recovery/{email}", response_model=Msg, status_code=status.HTTP_200_OK)
def recover_password(email: EmailStr, db: Session = Depends(get_session)):
    """
    Genera un token para resetear la contraseña y (simula) enviarlo por email.
    Por seguridad, siempre devuelve una respuesta exitosa para no revelar qué correos
    están registrados en el sistema.
    """
    user = db.exec(select(Usuario).where(Usuario.correo == email)).first()

    if user and user.estado == UsuarioEstado.ACTIVO:
        password_reset_token_expires = timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
        password_reset_token = create_access_token(
            subject=user.id, expires_delta=password_reset_token_expires
        )
        
        # En una aplicación real, aquí se enviaría un email al usuario.
        # Por ahora, lo imprimimos en la consola para desarrollo.
        print(f"--- INICIO SIMULACIÓN ENVÍO DE CORREO ---")
        print(f"Para: {email}")
        print(f"Asunto: Recuperación de Contraseña")
        print(f"Use este token para resetear su contraseña: {password_reset_token}")
        print(f"--- FIN SIMULACIÓN ENVÍO DE CORREO ---")

    return {"msg": "Si una cuenta con ese correo existe y está activa, se ha enviado un enlace para recuperar la contraseña."}

@router.post("/reset-password", response_model=Msg)
def reset_password(body: PasswordReset, db: Session = Depends(get_session)):
    """
    Resetea la contraseña usando un token válido.
    """
    try:
        payload = jwt.decode(body.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de reseteo inválido.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de reseteo inválido o expirado.")

    user = db.get(Usuario, user_id)
    if not user or user.estado != UsuarioEstado.ACTIVO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario es inválido o no está activo.",
        )

    user.hashed_password = hash_password(body.new_password)
    db.add(user)
    db.commit()

    return {"msg": "La contraseña ha sido actualizada exitosamente."}

@router.post("/refresh", response_model=Token)
def refresh_token_endpoint(
    body: TokenRefreshRequest,
    db: Session = Depends(get_session)
):
    """
    Valida un token de refresco y devuelve un nuevo access token y un nuevo refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de refresco inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        
        # Validamos explícitamente que sea un token de tipo refresh
        if user_id is None or token_type != "refresh":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        parsed_uuid = uuid.UUID(user_id)
    except ValueError:
        raise credentials_exception

    user = db.get(Usuario, parsed_uuid)
    if user is None or user.estado != UsuarioEstado.ACTIVO:
        raise credentials_exception

    access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": new_refresh_token
    }

@router.post("/change-password", response_model=Msg)
def change_password(
    body: PasswordChange,
    current_user: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    """
    Cambia la contraseña del usuario autenticado.
    Verifica la contraseña actual y actualiza el flag debe_cambiar_password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta."
        )

    current_user.hashed_password = hash_password(body.new_password)
    current_user.debe_cambiar_password = False
    
    db.add(current_user)
    db.commit()

    return {"msg": "La contraseña ha sido actualizada exitosamente."}