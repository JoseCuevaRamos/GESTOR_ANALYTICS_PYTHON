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
    # FUENTE DE VERDAD: columna.status_fijas (NO completed_at ni started_at)
    # Según documentación PHP:
    # - status_fijas='1' = En Progreso
    # - status_fijas='2' = Finalizado
    # - status_fijas=NULL = Columnas normales (Pendientes)
    # - id_columna NUNCA es NULL (garantizado por BD)
    
    # Filtrar solo tareas activas en columnas activas
    tareas = db.query(Tarea)\
        .join(Columna, Tarea.id_columna == Columna.id_columna)\
        .filter(
            Tarea.id_proyecto == id,
            Tarea.status == '0',      # Tareas no eliminadas
            Columna.status == '0'      # Columnas no eliminadas
        ).all()

    # Mapear columnas: id_columna -> status_fijas
    # status_fijas es STRING: '1', '2' o NULL (NO existe '0')
    columnas_map = {}
    try:
        columnas = db.query(Columna).filter(Columna.status == '0').all()
        columnas_map = {c.id_columna: c.status_fijas for c in columnas}
    except Exception:
        columnas_map = {}

    # Cycle Time: tiempo desde started_at hasta completed_at (solo si ambos existen)
    cycle_times = [
        (t.completed_at - t.started_at).total_seconds() / 60 
        for t in tareas 
        if t.started_at and t.completed_at
    ]
    avg_cycle_time = int(sum(cycle_times) / len(cycle_times)) if cycle_times else 0

    # Lead Time: tiempo desde created_at hasta completed_at
    lead_times = [
        (t.completed_at - t.created_at).total_seconds() / 60 
        for t in tareas 
        if t.created_at and t.completed_at
    ]
    avg_lead_time = int(sum(lead_times) / len(lead_times)) if lead_times else 0

    # CLASIFICACIÓN BASADA EN columna.status_fijas (FUENTE DE VERDAD)
    tareas_completadas = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) == '2'  # STRING '2', NO int
    ])
    
    tareas_en_progreso = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) == '1'  # STRING '1', NO int
    ])
    
    # Tareas pendientes: columnas con status_fijas=NULL (columnas normales)
    tareas_pendientes = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) is None  # NULL, NO '0'
    ])

    # VALIDACIÓN DE CONSISTENCIA: La suma debe ser igual al total
    total_tareas = len(tareas)
    suma_verificacion = tareas_completadas + tareas_en_progreso + tareas_pendientes
    
    # Si hay inconsistencia, ajustar para evitar porcentajes > 100%
    if suma_verificacion != total_tareas:
        # Registrar warning (en producción usar logging)
        print(f"⚠️ INCONSISTENCIA en proyecto {id}: {tareas_completadas} + {tareas_en_progreso} + {tareas_pendientes} = {suma_verificacion} != {total_tareas}")
        # Recalcular pendientes como diferencia
        tareas_pendientes = max(0, total_tareas - tareas_completadas - tareas_en_progreso)

    # Entregas a tiempo/tarde (solo tareas completadas con fecha límite)
    entregas_a_tiempo = 0
    entregas_tarde = 0
    for t in tareas:
        if t.completed_at and t.due_at:
            if t.completed_at <= t.due_at:
                entregas_a_tiempo += 1
            else:
                entregas_tarde += 1

    # Tareas asignadas (tienen id_asignado)
    tareas_asignadas = len([t for t in tareas if t.id_asignado is not None])

    # Velocidad: Tareas completadas en últimos 14 días / 14
    # Usar columna.status_fijas='2' Y completed_at (ambas condiciones)
    fecha_inicio_velocidad = datetime.now() - timedelta(days=14)
    tareas_completadas_recientes = len([
        t for t in tareas 
        if columnas_map.get(t.id_columna) == '2'  # En columna Finalizado
        and t.completed_at  # Tiene fecha de completado
        and t.completed_at >= fecha_inicio_velocidad  # En últimos 14 días
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

    # Rendimiento del equipo: Ponderado para Kanban
    # Completadas = 100%, En Progreso = 50%, Pendientes = 0%
    if total_tareas > 0:
        progreso_ponderado = (tareas_completadas * 1.0) + (tareas_en_progreso * 0.5)
        rendimiento_porcentaje = (progreso_ponderado / total_tareas) * 100
        # LIMITAR entre 0-100% para prevenir inconsistencias
        rendimiento_porcentaje = min(max(round(rendimiento_porcentaje, 1), 0.0), 100.0)
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
