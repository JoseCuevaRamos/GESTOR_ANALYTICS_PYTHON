
# Imagen base ligera de Python
FROM python:3.10-slim

# Evitar que Python genere archivos .pyc y usar stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias y entorno
COPY requirements.txt .
# Do NOT copy a local .env into the image for production. Environment
# variables should be injected by the hosting platform (Render).
#COPY .env .

# Instalar dependencias del sistema (necesarias para conectores MySQL si se usan)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-libmysqlclient-dev \
        build-essential \
    && pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y build-essential \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copiar el código fuente
COPY ./app ./app

# Exponer un puerto por defecto (documentacional). The container will bind
# to the PORT env var if provided by the platform. Default to 8080 for this
# project to match platform expectation.
EXPOSE 8080

# Ejecutar uvicorn enlazando al puerto proporcionado por la plataforma via
# la variable de entorno PORT. Render establece PORT en tiempo de ejecución;
# si no existe se usará 8080.
# Use shell form so environment variable expansion works.
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"
