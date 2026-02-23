# International Expansion Platform Container
FROM python:3.12-slim-bullseye

# Install system dependencies for internationalization
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libicu-dev \
    pkg-config \
    locales \
    locales-all \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set locale environment
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV LANGUAGE=en_US:en

# Generate locales for supported languages
RUN locale-gen en_GB.UTF-8 \
    && locale-gen en_US.UTF-8 \
    && locale-gen fr_FR.UTF-8 \
    && locale-gen de_DE.UTF-8 \
    && locale-gen es_ES.UTF-8 \
    && locale-gen it_IT.UTF-8 \
    && locale-gen nl_NL.UTF-8 \
    && locale-gen sv_SE.UTF-8 \
    && update-locale

# Create non-root user for security
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid 1000 --create-home appuser

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create translations directory
COPY ../../../libs/i18n/ ./translations/

# Security configurations
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]