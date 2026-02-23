# SelfMonitor IPO Readiness Infrastructure Dockerfile
# Enterprise governance and public company infrastructure for unicorn achievement

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libpq-dev \
        postgresql-client \
        redis-tools \
        libffi-dev \
        libssl-dev \
        libjpeg-dev \
        libpng-dev \
        wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Create non-root user
RUN adduser --disabled-password --gecos '' --uid 1000 ipoready && \
    chown -R ipoready:ipoready /app
USER ipoready

# Copy requirements and install Python dependencies
COPY --chown=ipoready:ipoready requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Add user's pip install path to PATH
ENV PATH="/home/ipoready/.local/bin:${PATH}"

# Copy application code
COPY --chown=ipoready:ipoready app/ ./app/

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/reports

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--access-log", "--log-level", "info"]