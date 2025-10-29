from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class TareaSchema(BaseModel):
    id_tarea: int
    id_proyecto: int
    nombre: str
    descripcion: Optional[str]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    archived_at: Optional[datetime]
    due_at: Optional[datetime]

    @field_validator('created_at', 'started_at', 'completed_at', 'archived_at', 'due_at', mode='before')
    def dt_to_str(cls, v):
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        orm_mode = True
