import os
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

# Usar el mismo secret y algoritmo que el backend PHP
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
ALGORITHM = "HS256"
APP_URL = os.getenv("APP_URL", "http://localhost:8000")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("token "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token no proporcionado")
    token = auth_header[6:]  # Quita "Token "
    from jose import jwt as jose_jwt
    try:
        payload = jose_jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat"]},
            issuer=APP_URL
        )
    except jose_jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    # Buscar usuario por username (sub)
    # user = db.query(User).filter_by(username=payload["sub"]).first()
    # if not user:
    #     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    # return user
    return payload  # Si no tienes modelo User, retorna el payload
"""
Manejo básico de autenticación JWT.
Incluye funciones para crear y verificar tokens.
"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional

# Clave secreta para firmar los tokens (en producción usar variable de entorno)
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT con los datos proporcionados."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """Verifica y decodifica un token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
