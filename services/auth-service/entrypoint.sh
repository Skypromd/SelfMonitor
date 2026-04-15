#!/bin/sh
set -e
chown -R appuser:appuser /data
exec runuser -u appuser -- "$@"
