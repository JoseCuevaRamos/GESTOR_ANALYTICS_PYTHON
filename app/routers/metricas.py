from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.tarea import Tarea
from app.models.columna import Columna
from app.models.usuario_rol import UsuarioRol
from datetime import datetime, timedelta

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/proyectos/{id}/metricas")
def metricas_proyecto(id: int, db: Session = Depends(get_db)):
    tareas = db.query(Tarea).filter(Tarea.id_proyecto == id).all()

    # Intentar leer columnas y mapear id_columna -> status_fijas. Si la tabla
    # `columnas` no existe o hay un error, hacemos fallback a la lógica previa
    # que considera completed_at/started_at.
    columnas_map = {}
    try:
        columnas = db.query(Columna).all()
        columnas_map = {c.id_columna: c.status_fijas for c in columnas}
    except Exception:
        # fallback: columnas_map vacío -> se usará la lógica por timestamps
        columnas_map = {}

    # Cycle Time (en minutos)
    cycle_times = [ (t.completed_at - t.started_at).total_seconds() / 60 for t in tareas if t.started_at and t.completed_at ]
    avg_cycle_time = int(sum(cycle_times) / len(cycle_times)) if cycle_times else 0

    # Lead Time (en minutos)
    lead_times = [ (t.completed_at - t.created_at).total_seconds() / 60 for t in tareas if t.created_at and t.completed_at ]
    avg_lead_time = int(sum(lead_times) / len(lead_times)) if lead_times else 0

    # Tareas completadas
    if columnas_map:
        # Contar como completada si su columna apunta a status_fijas = '2'
        tareas_completadas = len([t for t in tareas if t.id_columna and columnas_map.get(t.id_columna) == '2'])
    else:
        # Fallback: considerar completada si tiene completed_at
        tareas_completadas = len([t for t in tareas if t.completed_at])

    # Tareas en progreso
    if columnas_map:
        tareas_en_progreso = len([t for t in tareas if t.id_columna and columnas_map.get(t.id_columna) == '1'])
    else:
        tareas_en_progreso = len([t for t in tareas if t.started_at and not t.completed_at])

    # Tareas pendientes
    if columnas_map:
        tareas_pendientes = len([t for t in tareas if (t.id_columna is None) or (columnas_map.get(t.id_columna) is None)])
    else:
        tareas_pendientes = len([t for t in tareas if not t.started_at and not t.completed_at])

    # Note: archived_at field removed from Tarea model; archived count omitted

    # Entregas a tiempo/tarde
    entregas_a_tiempo = 0
    entregas_tarde = 0
    for t in tareas:
        if t.completed_at and t.due_at:
            if t.completed_at <= t.due_at:
                entregas_a_tiempo += 1
            else:
                entregas_tarde += 1

    # Total de tareas activas (status='0' significa tarea no eliminada)
    total_tareas = len([t for t in tareas if t.status == '0'])

    # Tareas asignadas (tienen id_asignado)
    tareas_asignadas = len([t for t in tareas if t.id_asignado is not None and t.status == '0'])

    # Velocidad: Tareas completadas en últimos 14 días / 14
    fecha_inicio_velocidad = datetime.now() - timedelta(days=14)
    if columnas_map:
        tareas_completadas_recientes = len([
            t for t in tareas 
            if t.id_columna 
            and columnas_map.get(t.id_columna) == '2'
            and t.completed_at 
            and t.completed_at >= fecha_inicio_velocidad
            and t.status == '0'
        ])
    else:
        tareas_completadas_recientes = len([
            t for t in tareas 
            if t.completed_at 
            and t.completed_at >= fecha_inicio_velocidad
            and t.status == '0'
        ])
    velocidad = round(tareas_completadas_recientes / 14, 2) if tareas_completadas_recientes > 0 else 0.0

    # Miembros activos: COUNT(DISTINCT id_usuario) de usuarios_roles WHERE status='0'
    try:
        miembros_activos = db.query(func.count(func.distinct(UsuarioRol.id_usuario)))\
            .filter(
                UsuarioRol.id_proyecto == id,
                UsuarioRol.status == '0'
            ).scalar() or 0
    except Exception:
        # Fallback si la tabla usuarios_roles no existe
        miembros_activos = 0

    # Rendimiento del equipo: Ponderado para Kanban/Trello
    # Completadas = 100%, En Progreso = 50%, Pendientes = 0%
    if total_tareas > 0:
        progreso_ponderado = (tareas_completadas * 1.0) + (tareas_en_progreso * 0.5)
        rendimiento_porcentaje = round((progreso_ponderado / total_tareas) * 100, 1)
    else:
        rendimiento_porcentaje = 0.0

    return {
        "cycle_time_promedio": avg_cycle_time,
        "lead_time_promedio": avg_lead_time,
        "tareas_completadas": tareas_completadas,
        "tareas_en_progreso": tareas_en_progreso,
        "tareas_pendientes": tareas_pendientes,
        "entregas_a_tiempo": entregas_a_tiempo,
        "entregas_tarde": entregas_tarde,
        "total_tareas": total_tareas,
        "tareas_asignadas": tareas_asignadas,
        "velocidad": velocidad,
        "miembros_activos": miembros_activos,
        "rendimiento_porcentaje": rendimiento_porcentaje
    }
