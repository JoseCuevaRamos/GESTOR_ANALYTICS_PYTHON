import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from jose import jwt as jose_jwt, JWTError, ExpiredSignatureError

from app.core.database import SessionLocal

# Configuración básica de JWT (en producción usar solo variables de entorno)
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_token(token: str) -> dict:
    """
    Verifica y decodifica un token JWT usando jose.

    - Usa la clave JWT_SECRET y algoritmo ALGORITHM.
    - Si el payload incluye 'iss' y APP_URL está configurado, valida que coincidan.
    """
    try:
        payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        logger.debug("verify_token: payload keys=%s", list(payload.keys()))

        token_iss = payload.get("iss")
        if APP_URL and token_iss is not None and token_iss != APP_URL:
            raise JWTError("Invalid issuer")

        return payload
    except ExpiredSignatureError:
        logger.info("verify_token: token expirado")
        raise
    except JWTError as exc:
        logger.warning("verify_token: JWTError %s", exc)
        raise


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    Dependencia de FastAPI para validar el header Authorization.

    Acepta encabezados con prefijo "Token " o "Bearer ".
    Devuelve el id de usuario obtenido de `payload['sub']` como entero
    o lanza HTTPException 401 si algo falla.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no proporcionado",
        )

    token = None
    auth_value = auth_header.strip()
    lower = auth_value.lower()
    if lower.startswith("token "):
        token = auth_value[6:]
    elif lower.startswith("bearer "):
        token = auth_value[7:]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Esquema de autorización no válido",
        )

    try:
        payload = verify_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error JWT: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error verificando token: {str(e)}",
        )

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin sub",
        )

    try:
        user_id = int(sub)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="sub del token no es un id numérico",
        )

    # Si posteriormente quieres devolver un modelo User en lugar del id,
    # puedes resolverlo aquí utilizando SQLAlchemy y el Session `db`.
    return user_id

