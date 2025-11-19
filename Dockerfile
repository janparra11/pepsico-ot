# Imagen base de Python
FROM python:3.12-slim

# Evitar archivos .pyc y mejorar logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el proyecto
COPY . /app/

# Comando de arranque de Django con gunicorn
# IMPORTANTE: "config.wsgi:application" porque tu proyecto se llama "config"
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:${PORT}"]
