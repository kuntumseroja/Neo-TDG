# Neo-TDG: SDLC Knowledge Engine
# Multi-stage Docker build for Streamlit deployment
# Works on: Hugging Face Spaces, Railway, Render, Google Cloud Run, Azure Container Apps

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=7860 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Use cloud config for deployment (Groq free tier by default)
RUN if [ -f config.cloud.yaml ]; then cp config.cloud.yaml config.yaml; fi

# Create knowledge_base directory for persistence
RUN mkdir -p /app/knowledge_base

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (7860 = HF Spaces default, override with $PORT for other platforms)
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${STREAMLIT_SERVER_PORT}/_stcore/health || exit 1

# Start Streamlit (uses $PORT env var if set, falls back to 7860)
CMD streamlit run app.py \
    --server.port=${PORT:-7860} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
