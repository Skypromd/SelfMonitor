#!/bin/bash
# Automated Backup Script for SelfMonitor FinTech Platform
# Enterprise-grade backup with encryption and cloud storage

set -e

# Configuration
DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/backups"
POSTGRES_BACKUP="$BACKUP_DIR/postgres/pg_backup_$DATE.sql.gz"
REDIS_BACKUP="$BACKUP_DIR/redis/redis_backup_$DATE.rdb"
LOG_FILE="$BACKUP_DIR/backup_$DATE.log"

# Environment variables
POSTGRES_HOST=${POSTGRES_HOST:-postgres-master}
POSTGRES_USER=${POSTGRES_USER:-user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
POSTGRES_DB=${POSTGRES_DB:-db_user_profile}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
S3_BUCKET=${S3_BUCKET:-selfmonitor-backups}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "Starting backup process for SelfMonitor platform..."

# PostgreSQL Backup
log "Creating PostgreSQL backup..."
export PGPASSWORD="$POSTGRES_PASSWORD"
if pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB --verbose --clean --no-owner --no-acl | gzip > $POSTGRES_BACKUP; then
    log "PostgreSQL backup completed successfully: $POSTGRES_BACKUP"
else
    log "ERROR: PostgreSQL backup failed"
    exit 1
fi

# Redis Backup
log "Creating Redis backup..."
if redis-cli -h redis-master -p 6379 -a redis_secure_password_2026 --rdb $REDIS_BACKUP; then
    log "Redis backup completed successfully: $REDIS_BACKUP"
else
    log "ERROR: Redis backup failed"
    exit 1
fi

# Encrypt backups
log "Encrypting backups..."
if [ ! -z "$BACKUP_ENCRYPTION_KEY" ]; then
    gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_KEY" --symmetric --cipher-algo AES256 $POSTGRES_BACKUP
    gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_KEY" --symmetric --cipher-algo AES256 $REDIS_BACKUP
    rm $POSTGRES_BACKUP $REDIS_BACKUP
    POSTGRES_BACKUP="$POSTGRES_BACKUP.gpg"
    REDIS_BACKUP="$REDIS_BACKUP.gpg"
    log "Backups encrypted successfully"
fi

# Upload to S3
if [ ! -z "$S3_ACCESS_KEY" ] && [ ! -z "$S3_SECRET_KEY" ]; then
    log "Uploading backups to S3..."
    aws configure set aws_access_key_id $S3_ACCESS_KEY
    aws configure set aws_secret_access_key $S3_SECRET_KEY
    
    if aws s3 cp $POSTGRES_BACKUP s3://$S3_BUCKET/postgres/ && \
       aws s3 cp $REDIS_BACKUP s3://$S3_BUCKET/redis/ && \
       aws s3 cp $LOG_FILE s3://$S3_BUCKET/logs/; then
        log "Backups uploaded to S3 successfully"
    else
        log "ERROR: Failed to upload backups to S3"
    fi
fi

# Cleanup old backups
log "Cleaning up old backups..."
find $BACKUP_DIR/postgres -name "pg_backup_*.sql.gz*" -mtime +$BACKUP_RETENTION_DAYS -delete
find $BACKUP_DIR/redis -name "redis_backup_*.rdb*" -mtime +$BACKUP_RETENTION_DAYS -delete
find $BACKUP_DIR -name "backup_*.log" -mtime +$BACKUP_RETENTION_DAYS -delete

# Health monitoring - send backup status
BACKUP_SIZE_PG=$(du -h $POSTGRES_BACKUP | cut -f1)
BACKUP_SIZE_REDIS=$(du -h $REDIS_BACKUP | cut -f1)

log "Backup completed successfully!"
log "PostgreSQL backup size: $BACKUP_SIZE_PG"
log "Redis backup size: $BACKUP_SIZE_REDIS"

# Send notification (webhook, Slack, etc.)
if [ ! -z "$BACKUP_WEBHOOK_URL" ]; then
    curl -X POST $BACKUP_WEBHOOK_URL \
        -H 'Content-Type: application/json' \
        -d "{\"message\": \"SelfMonitor backup completed successfully\", \"timestamp\": \"$DATE\", \"postgres_size\": \"$BACKUP_SIZE_PG\", \"redis_size\": \"$BACKUP_SIZE_REDIS\"}"
fi