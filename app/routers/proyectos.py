"""
Router para endpoints de proyectos.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.proyecto import Proyecto

from app.core.auth import get_current_user
from fastapi import Depends
from app.schemas.proyecto import ProyectosResponse, ProyectoSchema

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/espacios/{id}/proyectos", response_model=ProyectosResponse)
def listar_proyectos(id: int, id_usuario: int = Query(0), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Listar proyectos de un espacio, filtrados por usuario si se proporciona."""
    # Si NO se proporciona id_usuario, devolver TODOS los proyectos activos
    if id_usuario == 0:
        proyectos = db.query(Proyecto).filter(Proyecto.id_espacio == id, Proyecto.status == '0').all()
        count = len(proyectos)
        return {"proyecto": proyectos, "proyectoCount": count}
    # Si SÍ se proporciona id_usuario, devolver solo los proyectos donde es creador
    proyectos = db.query(Proyecto).filter(Proyecto.id_espacio == id, Proyecto.id_usuario_creador == id_usuario, Proyecto.status == '0').all()
    count = len(proyectos)
    return {"proyecto": proyectos, "proyectoCount": count}
