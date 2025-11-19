# Usar una imagen base de Python
FROM python:3.12-slim

# Crear carpeta de trabajo
WORKDIR /app

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# ⚠️ NUEVO: recopilar los archivos estáticos de Django
RUN python manage.py collectstatic --noinput

# Exponer el puerto interno del contenedor
EXPOSE 8000

# Comando de arranque
CMD gunicorn config.wsgi:application --bind 0.0.0.0:8000
