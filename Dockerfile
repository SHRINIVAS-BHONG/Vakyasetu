# ==============================================================================
# Unified Multi-Stage Dockerfile for Hugging Face Spaces & Cloud Deployment
# Runs React 18 UI + FastAPI Sanskrit NLP Engine in ONE Container on Port 7860
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build the React 18 Frontend
# ------------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/web/package*.json ./
RUN npm ci || npm install

COPY frontend/web/ ./
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Python Runtime with FastAPI & Paninian Linguistic Engine
# ------------------------------------------------------------------------------
FROM python:3.10-slim

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces requires running as non-root user (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR $HOME/app

# Install Python dependencies (with PyTorch CPU to keep image fast and lightweight)
COPY --chown=user:user backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source
COPY --chown=user:user backend/ $HOME/app/backend/

# Copy compiled React static assets into the expected path
COPY --from=frontend-builder --chown=user:user /frontend/dist $HOME/app/frontend/web/dist/

WORKDIR $HOME/app/backend

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
