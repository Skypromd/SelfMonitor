FROM alpine:latest

# Install required packages
RUN apk add --no-cache \
    postgresql-client \
    redis \
    curl \
    bash \
    gzip \
    tar \
    dcron \
    docker-cli \
    gnupg

# Create backup user
RUN adduser -D -s /bin/bash backup

# Create directories
RUN mkdir -p /backups/postgres /backups/redis /scripts

# Copy backup scripts
COPY backup.sh /scripts/backup.sh
COPY restore.sh /scripts/restore.sh
COPY entrypoint.sh /scripts/entrypoint.sh

# Windows CRLF breaks shebang ("no such file or directory" on exec)
RUN sed -i 's/\r$//' /scripts/*.sh

# Make scripts executable
RUN chmod +x /scripts/*.sh

# Cron must run as root; /backups volume must be writable for pg_dump output
RUN echo "0 2 * * * /scripts/backup.sh" | crontab -

WORKDIR /backups

CMD ["/bin/sh", "/scripts/entrypoint.sh"]
