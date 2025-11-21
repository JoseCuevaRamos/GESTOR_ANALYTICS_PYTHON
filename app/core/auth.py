"""
Manejo de autenticación compatible con tokens generados por el backend PHP.

Este módulo expone:
- create_access_token: utilidad para crear tokens (útil en pruebas).
- verify_token: decodifica un token con la clave configurada.
- get_current_user: dependencia de FastAPI que valida el header
  Authorization (acepta prefijos "Token " o "Bearer ") y devuelve
  el id del usuario (payload.sub) como entero.

Notas:
- Las variables de entorno esperadas: JWT_SECRET (clave), JWT_ALGORITHM,
  APP_URL (issuer opcional). Si no existe modelo `User` en SQLAlchemy,
  la dependencia devuelve el id del usuario en lugar de un objeto.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from jose import ExpiredSignatureError
from sqlalchemy.orm import Session
import logging

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Configuración: leer de entorno para que use los mismos valores que PHP
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "your-secret-key"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
APP_URL = os.getenv("APP_URL", None)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT con los datos proporcionados (útil para pruebas).

    En producción el token lo genera el backend PHP; esta función es opcional.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def generate_token_for_user(user, expires_hours: int = 2):
    """Genera un JWT con claims iat, exp, jti y sub (sub = id_usuario como string).

    No incluye 'iss' para mantener compatibilidad con tu petición.
    """
    import base64, secrets
    now = datetime.utcnow()
    future = now + timedelta(hours=expires_hours)
    jti = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')

    payload = {
        "iat": int(now.timestamp()),
        "exp": int(future.timestamp()),
        "jti": jti,
        "sub": str(getattr(user, 'id_usuario', user))
    }

    # Si hay APP_URL configurada, añadir 'iss' para que el token genere el issuer esperado
    if APP_URL:
        payload["iss"] = APP_URL

    # Log token generation metadata (no secrets)
    logger.debug("Generating token for user=%s expires_hours=%s jti=%s APP_URL=%s",
                 getattr(user, 'id_usuario', user), expires_hours, jti, APP_URL)
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str):
    """Verifica y decodifica un token con la clave configurada.

    Devuelve el payload (dict) o lanza JWTError/ExpiredSignatureError.
    """
    options = {"require": ["exp"]}
    try:
        # Decode without forcing jose to validate issuer so we can accept tokens
        # that don't include the `iss` claim (some PHP tokens omit it).
        logger.debug("verify_token: decoding token (first8)=%s APP_URL=%s", token[:8], APP_URL)
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options=options)
        logger.debug("verify_token: decoded payload keys=%s", list(payload.keys()))

        # If APP_URL is configured, validate issuer only when the token provides it.
        # This keeps compatibility with tokens that don't include `iss` while still
        # rejecting tokens that explicitly claim a different issuer.
        if APP_URL:
            token_iss = payload.get("iss")
            logger.debug("verify_token: token_iss=%s", token_iss)
            if token_iss is not None and token_iss != APP_URL:
                # raise a JWTError similar to jose when issuer mismatches
                logger.warning("verify_token: invalid issuer token_iss=%s expected=%s", token_iss, APP_URL)
                raise JWTError("Invalid issuer")

        return payload
    except ExpiredSignatureError:
        raise
    except JWTError:
        raise


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Dependencia de FastAPI para validar el header Authorization.

    Acepta encabezados con prefijo "Token " o "Bearer ". Devuelve el
    id de usuario obtenido de `payload['sub']` como entero. Si existe
    un modelo `User` y quieres devolver el objeto, se puede extender.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no proporcionado")

    token = None
    if auth_header.lower().startswith("token "):
        token = auth_header[6:]
    elif auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    else:
        # No reconoce el esquema
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Esquema de autorización no válido")

    try:
        payload = verify_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Error JWT: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Error verificando token: {str(e)}")

    # payload['sub'] debería contener el id del usuario según convención
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin sub")

    try:
        user_id = int(sub)
    except Exception:
        # si el sub no es un entero, devolver tal cual (o fallar)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sub del token no es un id numérico")

    # Intentar devolver el objeto User si existe; si no, devolvemos el id
    try:
        from app.models.models import User as UserModel
        user = db.query(UserModel).filter(UserModel.id_usuario == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
        return user
    except Exception:
        # No hay modelo User o hubo error al consultarlo: devolver solo user_id
        return user_id
