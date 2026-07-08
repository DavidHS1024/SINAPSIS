# ============================================================
# SINAPSIS API — Dockerfile de producción
# ============================================================
# Imagen ligera para servir SOLO la API de lectura.
# No incluye dependencias del pipeline (Playwright, spaCy, etc.)
# ============================================================

FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python (solo producción)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copiar código de la aplicación
COPY main.py .
COPY app/ app/

# Puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
