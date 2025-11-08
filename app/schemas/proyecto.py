"""
Esquema de respuesta para Proyecto.
"""
from pydantic import BaseModel
from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List

class ProyectoSchema(BaseModel):
    id_proyecto: int
    nombre: str
    descripcion: Optional[str]
    id_usuario_creador: int
    id_espacio: int
    status: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @field_validator('created_at', 'updated_at', mode='before')
    def dt_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        orm_mode = True

class ProyectosResponse(BaseModel):
    proyecto: List[ProyectoSchema]
    proyectoCount: int
