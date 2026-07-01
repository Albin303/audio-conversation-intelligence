# ========================================================
# Stage 1: Build Frontend
# ========================================================
FROM node:22-alpine AS frontend-builder
WORKDIR /app
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci && npm cache clean --force
COPY frontend/ ./
ENV NEXT_PUBLIC_API_URL=/api
RUN npm run build

# ========================================================
# Stage 2: Runtime Environment
# ========================================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1     PIP_DISABLE_PIP_VERSION_CHECK=1     NEXUS_UPLOADS_DIR=/app/uploads     NEXUS_DATABASE_DIR=/app/database     NEXUS_LOGS_DIR=/app/logs     NEXUS_SQLITE_PATH=/app/database/nexus_ai.db     HOME=/home/user     XDG_CACHE_HOME=/app/models_cache/.cache     HF_HOME=/app/models_cache/huggingface     TRANSFORMERS_CACHE=/app/models_cache/transformers     TORCH_HOME=/app/models_cache/torch     SPEECHBRAIN_CACHE=/app/models_cache/speechbrain

WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y --no-install-recommends     ffmpeg     libsndfile1     git     && rm -rf /var/lib/apt/lists/* /tmp/*

# Install python dependencies and download spaCy model
COPY requirements/production.txt ./requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt \
    && python -m spacy download en_core_web_sm \
    && rm -rf /root/.cache/pip /tmp/*

# Create application folders and user with UID 1000
RUN useradd -m -u 1000 user \
    && mkdir -p /app/uploads/audio /app/uploads/processed /app/uploads/reports /app/database /app/logs /app/models_cache \
    && chown -R user:user /app

# Copy application source code
COPY --chown=user:user src ./src
COPY --chown=user:user models ./models
COPY --chown=user:user data/processed ./data/processed
COPY --chown=user:user scripts ./scripts

# Copy static frontend export from Stage 1
COPY --chown=user:user --from=frontend-builder /app/frontend/out ./frontend/out

# Switch to non-root user
USER user

# Expose Hugging Face default port
EXPOSE 7860

# Run supervisor to start backend and workers
CMD ["python", "scripts/start.py"]
