from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


class Usuario(Base):
    __tablename__ = 'usuarios'
    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=True)
    correo = Column(String(255), nullable=True, unique=True)
    password_hash = Column(String(255), nullable=True)
    dni = Column(String(20), nullable=True)
    status = Column(Enum('0', '1', name='usuarios_status_enum'), default='0')
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # relaciones mínimas (si existen las tablas relacionadas)
    usuarios_roles = relationship("UsuarioRol", back_populates="usuario")
