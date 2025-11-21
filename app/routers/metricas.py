from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import SessionLocal
from app.core.auth import get_current_user
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

def format_time(seconds):
    """Convierte segundos a horas"""
    if not seconds or seconds <= 0:
        return 0
    hours = seconds / 3600
    return round(hours)

@router.get("/proyectos/{id}/metricas")
def metricas_proyecto(id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    print("\n" + "="*80)
    print(f"CALCULANDO MÉTRICAS PARA PROYECTO {id}")
    print("="*80)
    # Mostrar info del usuario autenticado (puede ser user_id o un objeto User)
    try:
        print(f"Usuario autenticado: {user}")
    except Exception:
        pass

    # Verificar que el usuario es líder del proyecto (id_rol == 1)
    def _is_project_leader(user_obj, proyecto_id, db_session: Session):
        try:
            user_id = user_obj.id_usuario if hasattr(user_obj, 'id_usuario') else int(user_obj)
        except Exception:
            return False
        rol = db_session.query(UsuarioRol).filter(
            UsuarioRol.id_proyecto == proyecto_id,
            UsuarioRol.id_usuario == user_id,
            UsuarioRol.id_rol == 1,
            UsuarioRol.status == '0'
        ).first()
        return rol is not None

    if not _is_project_leader(user, id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere ser líder del proyecto para acceder a esta ruta")
    
    tareas = db.query(Tarea)\
        .join(Columna, Tarea.id_columna == Columna.id_columna)\
        .filter(
            Tarea.id_proyecto == id,
            Tarea.status == '0',
            Columna.status == '0'
        ).all()

    columnas = db.query(Columna)\
        .filter(Columna.id_proyecto == id, Columna.status == '0')\
        .all()

    columnas_map = {c.id_columna: c.status_fijas for c in columnas}

    # Cycle Time
    cycle_times = []
    for t in tareas:
        if t.started_at and t.completed_at:
            diff_seconds = (t.completed_at - t.started_at).total_seconds()
            if diff_seconds > 0:
                cycle_times.append(diff_seconds)
    
    avg_cycle_time = format_time(sum(cycle_times) / len(cycle_times)) if cycle_times else 0

    # Lead Time
    lead_times = []
    for t in tareas:
        if t.created_at and t.completed_at:
            diff_seconds = (t.completed_at - t.created_at).total_seconds()
            if diff_seconds > 0:
                lead_times.append(diff_seconds)
    
    avg_lead_time = format_time(sum(lead_times) / len(lead_times)) if lead_times else 0

    # Conteo de tareas
    tareas_completadas = len([t for t in tareas if columnas_map.get(t.id_columna) == '2'])
    tareas_en_progreso = len([t for t in tareas if columnas_map.get(t.id_columna) == '1'])
    tareas_pendientes = len([t for t in tareas if columnas_map.get(t.id_columna) is None])
    total_tareas = len(tareas)

    # Entregas
    entregas_a_tiempo = 0
    entregas_tarde = 0
    for t in tareas:
        if t.completed_at and t.due_at:
            if t.completed_at <= t.due_at:
                entregas_a_tiempo += 1
            else:
                entregas_tarde += 1

    # Tareas asignadas
    tareas_asignadas = len([t for t in tareas if t.id_asignado is not None])

    # Rendimiento porcentaje
    if total_tareas > 0:
        progreso_ponderado = (tareas_completadas * 1.0) + (tareas_en_progreso * 0.5)
        rendimiento_porcentaje = (progreso_ponderado / total_tareas) * 100
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
        "rendimiento_porcentaje": rendimiento_porcentaje
    }


@router.get("/proyectos/{id}/burndown")
def burndown_chart(id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    """Genera datos para Burndown Chart - Solo lo necesario para el gráfico"""
    try:
        # Obtener tareas activas
        tareas = db.query(Tarea)\
            .join(Columna, Tarea.id_columna == Columna.id_columna)\
            .filter(
                Tarea.id_proyecto == id,
                Tarea.status == '0',
                Columna.status == '0'
            ).all()
        
        if not tareas:
            return {
                'progreso_diario': [],
                'linea_ideal': []
            }
        
        # Obtener columnas
        columnas = db.query(Columna)\
            .filter(Columna.id_proyecto == id, Columna.status == '0')\
            .all()
        
        columnas_map = {c.id_columna: c.status_fijas for c in columnas}
        
        # Calcular horas totales (24 horas por tarea por defecto)
        HORAS_POR_TAREA_DEFAULT = 24
        total_horas_estimadas = 0
        
        for t in tareas:
            tiempo = HORAS_POR_TAREA_DEFAULT
            if hasattr(t, 'tiempo_estimado') and t.tiempo_estimado:
                tiempo = t.tiempo_estimado
            elif hasattr(t, 'estimated_time') and t.estimated_time:
                tiempo = t.estimated_time
            total_horas_estimadas += tiempo
        
        HORAS_POR_DIA = 24
        total_dias_estimados = round(total_horas_estimadas / HORAS_POR_DIA, 2)
        
        # Fecha de inicio
        fechas_creacion = [t.created_at for t in tareas if t.created_at]
        fecha_inicio = min(fechas_creacion) if fechas_creacion else datetime.now()
        
        # Agrupar tareas completadas por fecha
        tareas_completadas_por_fecha = {}
        
        for t in tareas:
            if t.completed_at and columnas_map.get(t.id_columna) == '2':
                fecha_key = t.completed_at.date()
                
                tiempo_tarea = HORAS_POR_TAREA_DEFAULT
                if hasattr(t, 'tiempo_estimado') and t.tiempo_estimado:
                    tiempo_tarea = t.tiempo_estimado
                elif hasattr(t, 'estimated_time') and t.estimated_time:
                    tiempo_tarea = t.estimated_time
                
                if fecha_key not in tareas_completadas_por_fecha:
                    tareas_completadas_por_fecha[fecha_key] = {
                        'tareas_count': 0,
                        'horas_completadas': 0
                    }
                
                tareas_completadas_por_fecha[fecha_key]['tareas_count'] += 1
                tareas_completadas_por_fecha[fecha_key]['horas_completadas'] += tiempo_tarea
        
        # Generar progreso diario
        progreso_diario = []
        fecha_actual = fecha_inicio.date()
        fecha_hoy = datetime.now().date()
        dias_restantes = total_dias_estimados
        horas_restantes = total_horas_estimadas
        dia_indice = 0
        
        while fecha_actual <= fecha_hoy:
            if fecha_actual in tareas_completadas_por_fecha:
                horas_completadas_dia = tareas_completadas_por_fecha[fecha_actual]['horas_completadas']
                horas_restantes -= horas_completadas_dia
                dias_restantes = round(horas_restantes / HORAS_POR_DIA, 2)
            
            progreso_diario.append({
                'dia': dia_indice,
                'fecha': fecha_actual.isoformat(),
                'dias_restantes': max(dias_restantes, 0),
                'tareas_completadas_dia': tareas_completadas_por_fecha.get(fecha_actual, {}).get('tareas_count', 0)
            })
            
            fecha_actual += timedelta(days=1)
            dia_indice += 1
        
        # Calcular línea ideal
        duracion_total_dias = dia_indice
        linea_ideal = []
        
        if duracion_total_dias > 0:
            decremento_diario = total_dias_estimados / duracion_total_dias
            
            for i in range(duracion_total_dias + 1):
                dias_ideales_restantes = round(total_dias_estimados - (decremento_diario * i), 2)
                linea_ideal.append({
                    'dia': i,
                    'dias_restantes': max(dias_ideales_restantes, 0)
                })
        
        return {
            'progreso_diario': progreso_diario,
            'linea_ideal': linea_ideal
        }
        
    except Exception as e:
        print(f" ERROR en burndown_chart: {str(e)}")
        import traceback
        traceback.print_exc()
        raise