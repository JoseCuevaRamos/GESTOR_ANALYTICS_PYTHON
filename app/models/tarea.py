from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Tarea(Base):
    __tablename__ = "tareas"
    id_tarea = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(Integer, ForeignKey("proyectos.id_proyecto"))
    id_columna = Column(Integer, nullable=True)
    titulo = Column(String(255))
    descripcion = Column(Text, nullable=True)
    id_creador = Column(Integer, nullable=True)
    id_asignado = Column(Integer, nullable=True)
    position = Column(Integer, nullable=True)
    due_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    status = Column(String(1), default='0')
    prioridad = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    proyecto = relationship("Proyecto", back_populates="tareas")

# Import Proyecto at the end to resolve circular reference

