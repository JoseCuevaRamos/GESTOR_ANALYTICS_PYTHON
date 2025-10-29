
# Imagen base ligera de Python
FROM python:3.10-slim

# Evitar que Python genere archivos .pyc y usar stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias y entorno
COPY requirements.txt .
COPY .env .

# Instalar dependencias
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY ./app ./app

# Exponer el puerto en el que correrá la API
EXPOSE 8001

# Comando para ejecutar la aplicación FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
