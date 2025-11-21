from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class UsuarioRol(Base):
    __tablename__ = 'usuarios_roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey('usuarios.id_usuario'), nullable=False)
    id_rol = Column(Integer, ForeignKey('roles.id_rol'), nullable=False)
    id_espacio = Column(Integer, ForeignKey('espacios.id'), nullable=True)
    id_proyecto = Column(Integer, ForeignKey('proyectos.id_proyecto'), nullable=True)
    status = Column(Enum('0', '1', name='usuarios_roles_status_enum'), default='0')
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # Relaciones (inspiradas en el modelo PHP):
    # - `usuario` debe emparejar con `usuarios_roles` en el modelo Usuario
    # - `proyecto` es conveniente para acceder al proyecto relacionado
    # No añadimos `rol` ni `espacio` como relaciones si esos modelos no existen aún.
    usuario = relationship("Usuario", back_populates="usuarios_roles")
    proyecto = relationship("Proyecto", primaryjoin="UsuarioRol.id_proyecto==Proyecto.id_proyecto")
