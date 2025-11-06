import os
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt as jose_jwt, JWTError, ExpiredSignatureError

# Configuración (usar variables de entorno en producción)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Dependencia que valida JWT en header 'Authorization' con prefijo "Token ".
    Devuelve el id de usuario (claim 'sub') como int.
    Lanza HTTPException(status 401) si el token no existe, está expirado o es inválido.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("token "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no proporcionado")

    token = auth_header[6:]  # quitar "Token "

    try:
        payload = jose_jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat"]},
            issuer=APP_URL
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Error JWT: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Error desconocido: {str(e)}")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: falta claim 'sub'")

    try:
        user_id = int(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido: 'sub' no es numérico")

    # Aquí podrías validar existencia del usuario en BD usando `db` si lo deseas.
    return user_id


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Crear token JWT (útil para pruebas o emisión de tokens).
    Añade exp, iat e iss al payload.
    """
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now, "iss": APP_URL})
    encoded_jwt = jose_jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """Verifica y decodifica un token sin lanzar excepción (devuelve payload o None)."""
    try:
        payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM], issuer=APP_URL)
        return payload
    except JWTError:
        return None
