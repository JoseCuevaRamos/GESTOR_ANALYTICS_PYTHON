"""
Modelo Columna (ligero) para representar la tabla `columnas`.
Este modelo se usa para leer `status_fijas` y mapear tareas a estados como
"En Progreso" (1) o "Finalizado" (2). Si tu esquema usa nombres distintos,
ajusta este archivo.
"""
from sqlalchemy import Column, Integer, String
from app.core.database import Base


class Columna(Base):
    __tablename__ = 'columnas'
    id_columna = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=True)
    status_fijas = Column(String(10), nullable=True)  # ejemplo: '1', '2' o NULL
