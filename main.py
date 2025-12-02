"""
Archivo principal de la aplicación FastAPI.
Define el punto de entrada y un endpoint de prueba /health.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import proyectos
from app.routers import metricas
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS híbrido: leer orígenes permitidos desde ALLOWED_ORIGINS.
# En producción (Render) debes configurar ALLOWED_ORIGINS como la lista de orígenes
# permitidos (separados por comas). Para permitir cualquier origen usar '*'.
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4200,http://localhost:8000").strip()
if raw_origins == "*":
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proyectos.router)
app.include_router(metricas.router)


@app.get("/health")
def health_check():
    """Endpoint de prueba para verificar el estado de la API."""
    return {"status": "ok"}


@app.get("/deploy-check")
def deploy_check():
    """Comprobación básica útil en despliegue cuando la BD no está disponible.

    Devuelve si las variables de entorno críticas están presentes y una
    indicación de si la conexión debería usar SSL (detectado por 'tidb' en el host).
    NO devuelve secretos (p. ej. JWT_SECRET o DB_PASSWORD).
    """
    analytics_db_host = os.getenv("ANALYTICS_DB_HOST")
    db_host = analytics_db_host or os.getenv("DB_HOST")
    db_database = os.getenv("DB_DATABASE")
    analytics_db_port = os.getenv("ANALYTICS_DB_PORT")
    db_port = analytics_db_port or os.getenv("DB_PORT")
    analytics_db_user = os.getenv("ANALYTICS_DB_USERNAME")
    db_username = analytics_db_user or os.getenv("DB_USERNAME")
    jwt_present = bool(os.getenv("JWT_SECRET"))
    allowed_origins = os.getenv("ALLOWED_ORIGINS")

    ssl_suggested = False
    if db_host and "tidb" in db_host.lower():
        ssl_suggested = True

    # Indicar cuál variable se está usando (ANALYTICS_* tiene prioridad si existe)
    host_source = "ANALYTICS_DB_HOST" if analytics_db_host else ("DB_HOST" if os.getenv("DB_HOST") else None)
    port_source = "ANALYTICS_DB_PORT" if analytics_db_port else ("DB_PORT" if os.getenv("DB_PORT") else None)
    user_source = "ANALYTICS_DB_USERNAME" if analytics_db_user else ("DB_USERNAME" if os.getenv("DB_USERNAME") else None)

    return {
        "status": "ok",
        "env_checks": {
            "db_host": db_host,
            "db_host_source": host_source,
            "db_database": db_database,
            "db_port": db_port,
            "db_port_source": port_source,
            "db_username_present": bool(db_username),
            "db_username_source": user_source,
            "jwt_secret_set": jwt_present,
            "allowed_origins": allowed_origins,
            "ssl_suggested_by_host": ssl_suggested,
        },
    }
