from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
import logging

from app.core.database import SessionLocal
from app.models.usuario import Usuario
from app.core.auth import generate_token_for_user

router = APIRouter()

logger = logging.getLogger(__name__)

class LoginPayload(BaseModel):
    user: dict


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post('/login')
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user_params = payload.user
    correo = user_params.get('correo')
    password = user_params.get('password')

    logger.debug("login attempt correo=%s", correo)
    if not correo or not password:
        logger.warning("login missing fields correo=%s", correo)
        raise HTTPException(status_code=422, detail='correo o password: datos incompletos o inválidos')

    user = db.query(Usuario).filter(Usuario.correo == correo).first()
    if not user:
        logger.info("login failed user not found correo=%s", correo)
        raise HTTPException(status_code=422, detail='correo o password: es incorrecto')

    if getattr(user, 'status', '0') != '0':
        logger.info("login denied user removed id=%s correo=%s", getattr(user, 'id_usuario', None), correo)
        raise HTTPException(status_code=422, detail='Acceso denegado: usuario eliminado.')

    # Detectar si es temporal
    es_temporal = (getattr(user, 'nombre', None) == 'Temporal' and getattr(user, 'dni', None) is None)
    if es_temporal:
        return {
            'message': 'Usuario temporal detectado. Debe completar su registro.',
            'user': {
                'id_usuario': user.id_usuario,
                'correo': user.correo,
                'esTemporal': True
            }
        }

    # Verificar contraseña usando passlib bcrypt
    pw_hash = getattr(user, 'password_hash', None)
    try:
        if not pw_hash or not bcrypt.verify(password, pw_hash):
            logger.info("login failed invalid password correo=%s", correo)
            raise HTTPException(status_code=422, detail='correo o password: es incorrecto')
    except Exception as e:
        logger.exception("Error verificando contraseña para correo=%s: %s", correo, str(e))
        raise HTTPException(status_code=500, detail='Error interno verificando contraseña')

    token = generate_token_for_user(user, expires_hours=2)
    logger.debug("login success id_usuario=%s correo=%s token_first8=%s", user.id_usuario, correo, (token[:8] if token else None))

    user_data = {
        'id_usuario': user.id_usuario,
        'correo': user.correo,
        'token': token
    }

    return {'user': user_data}
