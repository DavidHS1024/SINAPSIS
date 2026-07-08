# ============================================================
# SINAPSIS API — Dockerfile de producción
# ============================================================
# Imagen para servir la API de lectura y ejecutar el pipeline
# ============================================================

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Instalar dependencias del sistema para psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegador para Playwright
RUN playwright install chromium

# Instalar modelo de spaCy
RUN pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_md-3.7.0/es_core_news_md-3.7.0.tar.gz

# Copiar código de la aplicación
COPY . .

# Puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
