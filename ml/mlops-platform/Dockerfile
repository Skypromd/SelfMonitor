FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    vim \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create directories for MLflow artifacts
RUN mkdir -p /app/mlruns /app/artifacts

# Create non-root user
RUN useradd --create-home --uid 1001 mlflow
RUN chown -R mlflow:mlflow /app
USER mlflow

# Expose ports
EXPOSE 5000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command (can be overridden)
CMD ["python", "src/mlflow_server.py"]