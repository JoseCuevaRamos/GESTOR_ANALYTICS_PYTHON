"""
Modelo Columna para representar la tabla `columnas`.

DOCUMENTACIÓN SEGÚN BACKEND PHP:
- status_fijas: ENUM('1', '2') NULL
  - '1' = Columna fija "En Progreso"
  - '2' = Columna fija "Finalizado"
  - NULL = Columna normal (pendientes)
  - ⚠️ NO existe '0'
  
- status: ENUM('0', '1')
  - '0' = Columna activa (visible)
  - '1' = Columna eliminada (soft delete)
"""
from sqlalchemy import Column, Integer, String, DateTime, func
from app.core.database import Base


class Columna(Base):
    __tablename__ = 'columnas'
    
    id_columna = Column(Integer, primary_key=True, autoincrement=True)
    id_proyecto = Column(Integer, nullable=False)  # ← AGREGADO
    nombre = Column(String(255), nullable=True)
    color = Column(String(50), nullable=True)  # ← AGREGADO (opcional)
    posicion = Column(Integer, nullable=True)  # ← AGREGADO (opcional)
    tipo_columna = Column(String(50), nullable=True)  # ← AGREGADO (opcional)
    status_fijas = Column(String(10), nullable=True)  # '1', '2' o NULL
    status = Column(String(1), nullable=False, default='0')  # '0' activa, '1' eliminada
    created_at = Column(DateTime, server_default=func.now())  # ← AGREGADO (opcional)
    updated_at = Column(DateTime, onupdate=func.now())  # ← AGREGADO (opcional)