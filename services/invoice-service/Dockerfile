FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_NO_INTERACTION 1
ENV POETRY_VENV_IN_PROJECT 1
ENV POETRY_CACHE_DIR /opt/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libfreetype6-dev \
    libjpeg-dev \
    libpng-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-dev && rm -rf $POETRY_CACHE_DIR

# Copy application
COPY . .

# Create directories
RUN mkdir -p /app/static /app/templates /tmp/invoices

# Set permissions
RUN chmod -R 755 /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the app
CMD ["poetry", "run", "python", "-m", "app.main"]