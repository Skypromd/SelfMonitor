#!/bin/bash
# Backup Service Entrypoint

# Start cron daemon
crond

# Run initial backup
/scripts/backup.sh

# Keep container running
tail -f /dev/null