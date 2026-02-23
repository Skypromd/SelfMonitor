FROM python:3.12-slim

# Metadata
LABEL name="selfmonitor-recommendation-engine"
LABEL version="2.0.0"
LABEL description="Real-time AI-powered recommendation engine for financial optimization"

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ./requirements.txt /code/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy application code
COPY ./app /code/app

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser
RUN chown -R appuser:appuser /code
USER appuser

# Expose port
EXPOSE 8006

# Environment variables
ENV PYTHONPATH=/code
ENV PORT=8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8006/health || exit 1

# Run the service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]