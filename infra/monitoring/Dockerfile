FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
        psycopg2-binary \
        redis \
        requests \
        prometheus-client \
        schedule \
        smtplib \
        email-validator

# Create app directory
WORKDIR /app

# Copy monitoring scripts
COPY db_monitor.py .
COPY health_check.py .
COPY alerts.py .
COPY entrypoint.py .
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create monitoring user
RUN useradd -m -s /bin/bash monitor
USER monitor

CMD ["python", "entrypoint.py"]