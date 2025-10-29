"""
Modelo Proyecto para SQLAlchemy.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func

from sqlalchemy.orm import relationship
from app.core.database import Base


class Proyecto(Base):
    __tablename__ = 'proyectos'
    id_proyecto = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(Text, nullable=True)
    id_usuario_creador = Column(Integer, nullable=False)
    id_espacio = Column(Integer, nullable=False)
    status = Column(String(1), default='0')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    tareas = relationship("Tarea", back_populates="proyecto")

# Import Tarea at the end to resolve circular reference

