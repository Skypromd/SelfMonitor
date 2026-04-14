#!/bin/bash
# Automated Restore Script for SelfMonitor FinTech Platform
# Enterprise-grade restore from encrypted cloud storage

set -e

# Configuration
BACKUP_DIR="/backups"
LOG_FILE="$BACKUP_DIR/restore_$(date +"%Y%m%d_%H%M%S").log"

# Environment variables
POSTGRES_HOST=${POSTGRES_HOST:-postgres-master}
POSTGRES_USER=${POSTGRES_USER:-user}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
POSTGRES_DB=${POSTGRES_DB:-db_user_profile}
S3_BUCKET=${S3_BUCKET:-selfmonitor-backups}
BACKUP_ENCRYPTION_KEY=${BACKUP_ENCRYPTION_KEY:-}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "Starting restore process for SelfMonitor platform..."

# Function to restore PostgreSQL
restore_postgres() {
    local backup_file=$1
    log "Restoring PostgreSQL from $backup_file..."
    
    # Check if backup is encrypted
    if [[ "$backup_file" == *.gpg ]]; then
        if [ -z "$BACKUP_ENCRYPTION_KEY" ]; then
            log "ERROR: Backup is encrypted but no encryption key provided"
            return 1
        fi
        log "Decrypting PostgreSQL backup..."
        gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_KEY" --decrypt "$backup_file" | gunzip | psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB || return 1
    else
        # Assume compressed with gzip
        gunzip -c "$backup_file" | psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB || return 1
    fi
    
    log "PostgreSQL restore completed successfully"
    return 0
}

# Function to restore Redis
restore_redis() {
    local backup_file=$1
    log "Restoring Redis from $backup_file..."
    
    REDIS_CLI=(redis-cli -h redis-master -p 6379)
    if [ -n "${REDIS_PASSWORD:-}" ]; then
        REDIS_CLI+=(-a "$REDIS_PASSWORD")
    fi
    
    # Check if backup is encrypted
    if [[ "$backup_file" == *.gpg ]]; then
        if [ -z "$BACKUP_ENCRYPTION_KEY" ]; then
            log "ERROR: Backup is encrypted but no encryption key provided"
            return 1
        fi
        log "Decrypting Redis backup..."
        gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_KEY" --decrypt "$backup_file" > /tmp/redis_restore.rdb || return 1
        if "${REDIS_CLI[@]}" --rdb /tmp/redis_restore.rdb; then
            rm /tmp/redis_restore.rdb
        else
            log "ERROR: Redis restore failed"
            rm /tmp/redis_restore.rdb
            return 1
        fi
    else
        if "${REDIS_CLI[@]}" --rdb "$backup_file"; then
            log "Redis restore completed successfully"
        else
            log "ERROR: Redis restore failed"
            return 1
        fi
    fi
    
    return 0
}

# Check for backup file arguments
if [ $# -eq 0 ]; then
    log "No backup files specified"
    log "Usage: $0 <postgres_backup_file> [redis_backup_file]"
    exit 1
fi

POSTGRES_BACKUP_FILE=$1
REDIS_BACKUP_FILE=${2:-}

# Check if files exist
if [ ! -f "$POSTGRES_BACKUP_FILE" ]; then
    log "ERROR: PostgreSQL backup file not found: $POSTGRES_BACKUP_FILE"
    exit 1
fi

# Restore PostgreSQL
export PGPASSWORD="$POSTGRES_PASSWORD"
if restore_postgres "$POSTGRES_BACKUP_FILE"; then
    log "PostgreSQL restored successfully"
else
    log "ERROR: PostgreSQL restore failed"
    exit 1
fi

# Restore Redis if provided
if [ -n "$REDIS_BACKUP_FILE" ]; then
    if [ ! -f "$REDIS_BACKUP_FILE" ]; then
        log "ERROR: Redis backup file not found: $REDIS_BACKUP_FILE"
        exit 1
    fi
    
    if restore_redis "$REDIS_BACKUP_FILE"; then
        log "Redis restored successfully"
    else
        log "ERROR: Redis restore failed"
        exit 1
    fi
fi

log "Restore completed successfully!"

# Verify restore by checking data
log "Verifying restore integrity..."
POSTGRES_TABLES=$($PSQL -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")
log "PostgreSQL tables found: $POSTGRES_TABLES"

log "Restore process finished"
