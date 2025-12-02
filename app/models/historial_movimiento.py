from sqlalchemy import Column, Integer, ForeignKey, DateTime, func
from app.core.database import Base


class HistorialMovimiento(Base):
    __tablename__ = "historial_movimientos"

    # Clave primaria compuesta solo a nivel de ORM para que SQLAlchemy
    # pueda identificar filas, no es necesario que exista una PK en la BD.
    id_tarea = Column(Integer, ForeignKey("tareas.id_tarea"), primary_key=True)
    timestamp = Column(DateTime, primary_key=True, server_default=func.now())

    id_columna_anterior = Column(Integer, ForeignKey("columnas.id_columna"), nullable=True)
    id_columna_nueva = Column(Integer, ForeignKey("columnas.id_columna"), nullable=False)
    id_usuario = Column(Integer, nullable=True)

