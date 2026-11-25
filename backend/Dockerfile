# ============================================================
# Dockerfile — Guardrail App (FastAPI + ONNX Runtime)
# ============================================================
# Base image: Python 3.11 slim untuk ukuran minimal
# ============================================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="Backend & Infrastructure Team"
LABEL description="Prompt Injection Guardrail — FastAPI + ONNX Classifier"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install system dependencies yang dibutuhkan oleh onnxruntime
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements terlebih dahulu (layer caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy static files (Web Chat UI)
COPY static/ ./static/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run FastAPI with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
