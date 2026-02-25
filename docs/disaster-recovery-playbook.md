# 🚨 DISASTER RECOVERY PLAYBOOK - SELFMONITOR
**RTO Target:** 15 minutes | **RPO Target:** 5 minutes | **Availability:** 99.99%

---

## 🎯 INCIDENT SEVERITY LEVELS

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| **P0** | Complete platform outage | 5 minutes | CEO + CTO |
| **P1** | Critical service degradation | 15 minutes | Engineering Lead |
| **P2** | Non-critical service issues | 1 hour | On-call Engineer |
| **P3** | Minor performance issues | 4 hours | Regular Support |

---

## 🔧 AUTOMATED RECOVERY PROCEDURES

### **Database Failover (PostgreSQL)**
```bash
#!/bin/bash
# Automated PostgreSQL failover script

MASTER_DB=\"postgresql-primary\"
REPLICA_DB=\"postgresql-replica\"
HEALTH_CHECK_URL=\"http://postgresql-primary:5432\"

# Check master health
if ! curl -f $HEALTH_CHECK_URL; then
    echo \"Master DB down, initiating failover...\"
    
    # Promote replica to master
    kubectl patch postgresql postgresql-primary --type='merge' -p='{\"spec\":{\"mode\":\"replica\"}}'
    kubectl patch postgresql postgresql-replica --type='merge' -p='{\"spec\":{\"mode\":\"primary\"}}'
    
    # Update service endpoints
    kubectl patch service postgresql-service -p '{\"spec\":{\"selector\":{\"role\":\"replica\"}}}'
    
    # Alert operations team
    curl -X POST $SLACK_WEBHOOK -d '{\"text\":\"🚨 PostgreSQL failover completed\"}'
    
    echo \"Failover completed in $(date)\"
fi
```

### **Service Auto-Recovery**
```yaml
# Kubernetes auto-recovery configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    spec:
      containers:
      - name: auth-service
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: \"512Mi\"
            cpu: \"250m\"
          limits:
            memory: \"1Gi\"
            cpu: \"500m\"
```

---

## 💾 BACKUP & RESTORE PROCEDURES

### **Daily Automated Backups**
```bash
#!/bin/bash
# PostgreSQL automated backup script (runs daily at 2 AM)

BACKUP_DIR=\"/backup/postgresql\"
S3_BUCKET=\"selfmonitor-backups\"
DATE=$(date +%Y%m%d_%H%M%S)

# Create database dump
pg_dump postgresql://user:password@postgres:5432/production > $BACKUP_DIR/selfmonitor_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/selfmonitor_$DATE.sql

# Upload to S3 with encryption
aws s3 cp $BACKUP_DIR/selfmonitor_$DATE.sql.gz s3://$S3_BUCKET/postgresql/ --sse AES256

# Verify backup integrity
aws s3api head-object --bucket $S3_BUCKET --key postgresql/selfmonitor_$DATE.sql.gz

# Clean up old local backups (keep 7 days)
find $BACKUP_DIR -name \"*.sql.gz\" -mtime +7 -delete

# Alert if backup failed
if [ $? -ne 0 ]; then
    curl -X POST $SLACK_WEBHOOK -d '{\"text\":\"🚨 Backup failed for '$DATE'\"}'
fi
```

### **Point-in-Time Recovery**
```bash
#!/bin/bash
# PostgreSQL Point-in-Time Recovery (PITR)

RESTORE_TIME=\"2026-02-24 14:30:00\"
BACKUP_FILE=\"s3://selfmonitor-backups/postgresql/selfmonitor_20260224_020000.sql.gz\"

# Download latest backup before restore time
aws s3 cp $BACKUP_FILE ./restore_backup.sql.gz
gunzip restore_backup.sql.gz

# Stop application services
kubectl scale deployment auth-service --replicas=0
kubectl scale deployment user-profile-service --replicas=0
kubectl scale deployment transactions-service --replicas=0

# Restore database
psql postgresql://user:password@postgres:5432/production < restore_backup.sql

# Apply WAL logs for PITR
# (Requires WAL-E or similar tool for continuous archiving)

# Restart services
kubectl scale deployment auth-service --replicas=3
kubectl scale deployment user-profile-service --replicas=3
kubectl scale deployment transactions-service --replicas=3

echo \"Point-in-time recovery completed to $RESTORE_TIME\"
```

---

## 🚨 INCIDENT RESPONSE PROCEDURES

### **P0: Complete Platform Outage**

**Immediate Actions (0-5 minutes):**
1. **Alert Team:** Automatic PagerDuty alerts + Slack notifications
2. **Status Page:** Update https://status.selfmonitor.ai
3. **Traffic Routing:** Activate maintenance mode
4. **Initial Assessment:** Check infrastructure health dashboard

**Recovery Actions (5-15 minutes):**
```bash
# Emergency recovery checklist
echo \"Starting P0 incident response...\"

# Check all critical services
kubectl get pods -n selfmonitor | grep -v Running

# Check database connectivity  
kubectl exec -it postgres-0 -- psql -c \"SELECT 1\"

# Check external dependencies
curl -f https://api.openbanking.org.uk/
curl -f https://developer.hmrc.gov.uk/

# Rollback to last known good deployment if needed
kubectl rollout undo deployment/auth-service
kubectl rollout undo deployment/user-profile-service

# Scale up replicas if resource constrained
kubectl scale deployment auth-service --replicas=5
```

### **Communication Templates**

**Customer Communication:**
```
🚨 INCIDENT ALERT 
We're currently experiencing technical difficulties affecting our platform. 
Our engineering team is actively working on a resolution.
Estimated resolution: 15 minutes
Status updates: https://status.selfmonitor.ai
```

**Internal Communication:**
```
P0 INCIDENT - Platform Outage
Started: [TIME]
Impact: Complete service unavailability  
Actions: Database failover in progress
ETA: 15 minutes
War room: #incident-response
```

---

## 📊 MONITORING & ALERTING

### **Critical Alerts Configuration**
```yaml
# Prometheus alerting rules
groups:
- name: selfmonitor.critical
  rules:
  - alert: ServiceDown
    expr: up{job=~\"auth-service|user-profile-service\"} == 0
    for: 30s
    labels:
      severity: critical
    annotations:
      summary: \"{{ $labels.job }} service is down\"
      
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~\"5..\"}[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: \"High error rate detected: {{ $value }}\"
      
  - alert: DatabaseConnectionsFull
    expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.9
    for: 1m
    labels:
      severity: warning
    annotations:
      summary: \"PostgreSQL connection pool nearly full\"
```

### **Health Check Endpoints**
```python
# Enhanced health checks for all services
@app.get(\"/health\")  
async def health_check():
    return {
        \"status\": \"healthy\",
        \"timestamp\": datetime.now(timezone.utc).isoformat(),
        \"version\": os.getenv(\"APP_VERSION\", \"unknown\"),
        \"database\": await check_database_connection(),
        \"redis\": await check_redis_connection(),
        \"external_apis\": await check_external_dependencies()
    }

@app.get(\"/ready\")
async def readiness_check():
    # Only return 200 if service is ready to serve traffic
    if await service_is_ready():
        return {\"status\": \"ready\"}
    else:
        raise HTTPException(status_code=503, detail=\"Service not ready\")
```

---

## 🧪 DISASTER RECOVERY TESTING

### **Monthly DR Drill Schedule**
- **Week 1:** Database failover test
- **Week 2:** Complete infrastructure failure simulation
- **Week 3:** Security incident response drill  
- **Week 4:** Data corruption and restore test

### **Automated DR Testing**
```bash
#!/bin/bash
# Monthly automated DR test

echo \"Starting DR test at $(date)\"

# Test database backup/restore
./scripts/backup-test.sh

# Test service failover
./scripts/failover-test.sh

# Test monitoring alerts
./scripts/alert-test.sh

# Generate DR test report
./scripts/generate-dr-report.sh

echo \"DR test completed at $(date)\"
```

---

## 📋 POST-INCIDENT REVIEW

### **Blameless Post-Mortem Template**
1. **Timeline:** Detailed incident timeline
2. **Root Cause:** Technical and process failures
3. **Impact:** Customer and business impact assessment  
4. **Action Items:** Specific improvements with owners
5. **Follow-up:** Implementation timeline and validation

### **Continuous Improvement**
- Monthly review of incident trends
- Quarterly DR plan updates
- Annual full-scale disaster simulation
- Regular training for all engineering staff

---

**Emergency Contacts:**
- **Engineering Lead:** +44 7700 900000
- **CTO:** +44 7700 900001  
- **CEO:** +44 7700 900002
- **AWS Support:** Premium Support (24/7)

**Last Updated:** February 24, 2026
**Next Review:** May 24, 2026