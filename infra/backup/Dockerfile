FROM alpine:latest

# Install required packages
RUN apk add --no-cache \
    postgresql15-client \
    redis \
    curl \
    awscli \
    bash \
    gzip \
    tar \
    cron \
    docker-cli

# Create backup user
RUN adduser -D -s /bin/bash backup

# Create directories
RUN mkdir -p /backups/postgres /backups/redis /scripts

# Copy backup scripts
COPY backup.sh /scripts/backup.sh
COPY restore.sh /scripts/restore.sh
COPY entrypoint.sh /scripts/entrypoint.sh

# Make scripts executable
RUN chmod +x /scripts/*.sh

# Set up cron job
RUN echo "0 2 * * * /scripts/backup.sh" | crontab -

USER backup
WORKDIR /backups

CMD ["/scripts/entrypoint.sh"]