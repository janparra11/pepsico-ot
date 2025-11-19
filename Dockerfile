# Usar una imagen base de Python
FROM python:3.12-slim

# Crear carpeta de trabajo
WORKDIR /app

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del proyecto
COPY . .

# Exponer el puerto interno del contenedor
EXPOSE 8000

# Comando de arranque: usa PORT si existe, si no 8000
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
