#!/usr/bin/env python3
"""
Enterprise Database Health Monitoring System
Automated failover detection and alerting for SelfMonitor FinTech Platform
"""

import os
import time
import logging
import schedule
import psycopg2
import redis
import requests
from datetime import datetime
from prometheus_client import start_http_server, Gauge, Counter
from alerts import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/monitoring/db_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
postgres_up = Gauge('postgres_up', 'PostgreSQL server availability', ['server'])
postgres_connections = Gauge('postgres_active_connections', 'Active PostgreSQL connections', ['server'])
postgres_replication_lag = Gauge('postgres_replication_lag_seconds', 'PostgreSQL replication lag in seconds')
redis_up = Gauge('redis_up', 'Redis server availability', ['server'])
redis_memory_usage = Gauge('redis_memory_usage_bytes', 'Redis memory usage in bytes', ['server'])
failover_events = Counter('database_failover_events_total', 'Total number of failover events', ['type'])

class DatabaseMonitor:
    def __init__(self):
        self.postgres_master_host = os.getenv('POSTGRES_MASTER_HOST', 'postgres-master')
        self.postgres_replica_host = os.getenv('POSTGRES_REPLICA_HOST', 'postgres-replica')
        self.redis_master_host = os.getenv('REDIS_MASTER_HOST', 'redis-master')
        self.redis_sentinels = os.getenv('REDIS_SENTINELS', 'redis-sentinel-1:26379').split(',')
        self.monitoring_interval = int(os.getenv('MONITORING_INTERVAL', 10))
        
        self.alert_manager = AlertManager()
        
        # Connection parameters
        self.pg_params = {
            'user': 'user',
            'password': 'password',
            'database': 'db_user_profile',
            'port': 5432
        }
        
        # Last known state
        self.last_postgres_master_up = True
        self.last_ 	_master_up = True
        
        logger.info("Database Monitor initialized")
    
    def check_postgres_health(self, host, server_name):
        """Check PostgreSQL server health and metrics"""
        try:
            conn = psycopg2.connect(host=host, **self.pg_params)
            cursor = conn.cursor()
            
            # Check if server is alive
            cursor.execute("SELECT 1")
            postgres_up.labels(server=server_name).set(1)
            
            # Get active connections
            cursor.execute("""
                SELECT count(*) 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active_connections = cursor.fetchone()[0]
            postgres_connections.labels(server=server_name).set(active_connections)
            
            # Check replication lag (only for master)
            if server_name == 'master':
                cursor.execute("""
                    SELECT CASE 
                        WHEN pg_is_in_recovery() = FALSE THEN 0
                        ELSE EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))
                    END
                """)
                lag = cursor.fetchone()[0] or 0
                postgres_replication_lag.set(lag)
            
            cursor.close()
            conn.close()
            
            logger.info(f"PostgreSQL {server_name} is healthy - {active_connections} active connections")
            return True
            
        except Exception as e:
            logger.error(f"PostgreSQL {server_name} health check failed: {e}")
            postgres_up.labels(server=server_name).set(0)
            
            # Alert if master is down
            if server_name == 'master' and self.last_postgres_master_up:
                self.alert_manager.send_critical_alert(
                    f"🚨 PostgreSQL Master DOWN!",
                    f"PostgreSQL master server ({host}) is not responding.\nError: {e}\nTime: {datetime.now()}"
                )
                failover_events.labels(type='postgres').inc()
                self.last_postgres_master_up = False
            
            return False
    
    def check_redis_health(self, host, server_name):
        """Check Redis server health and metrics"""
        try:
            r = redis.Redis(host=host, port=6379, password='redis_secure_password_2026', decode_responses=True)
            
            # Ping test
            r.ping()
            redis_up.labels(server=server_name).set(1)
            
            # Get memory usage
            info = r.info('memory')
            memory_usage = info.get('used_memory', 0)
            redis_memory_usage.labels(server=server_name).set(memory_usage)
            
            logger.info(f"Redis {server_name} is healthy - {memory_usage} bytes used")
            return True
            
        except Exception as e:
            logger.error(f"Redis {server_name} health check failed: {e}")
            redis_up.labels(server=server_name).set(0)
            
            # Alert if master is down
            if server_name == 'master' and self.last_redis_master_up:
                self.alert_manager.send_critical_alert(
                    f"🚨 Redis Master DOWN!",
                    f"Redis master server ({host}) is not responding.\nError: {e}\nTime: {datetime.now()}"
                )
                failover_events.labels(type='redis').inc()
                self.last_redis_master_up = False
            
            return False
    
    def check_sentinel_health(self):
        """Check Redis Sentinel cluster health"""
        healthy_sentinels = 0
        for sentinel_addr in self.redis_sentinels:
            try:
                host, port = sentinel_addr.split(':')
                r = redis.Redis(host=host, port=int(port), decode_responses=True)
                r.ping()
                healthy_sentinels += 1
            except Exception as e:
                logger.warning(f"Sentinel {sentinel_addr} is not responding: {e}")
        
        if healthy_sentinels < 2:  # Need at least 2 sentinels for quorum
            self.alert_manager.send_warning_alert(
                "⚠️ Redis Sentinel Quorum At Risk",
                f"Only {healthy_sentinels} out of {len(self.redis_sentinels)} sentinels are healthy.\nQuorum may be lost!"
            )
        
        logger.info(f"Redis Sentinel health: {healthy_sentinels}/{len(self.redis_sentinels)} healthy")
        return healthy_sentinels
    
    def run_health_checks(self):
        """Run all health checks"""
        logger.info("Starting database health checks...")
        
        # PostgreSQL checks
        postgres_master_healthy = self.check_postgres_health(self.postgres_master_host, 'master')
        postgres_replica_healthy = self.check_postgres_health(self.postgres_replica_host, 'replica')
        
        # Redis checks
        redis_master_healthy = self.check_redis_health(self.redis_master_host, 'master')
        
        # Sentinel checks
        healthy_sentinels = self.check_sentinel_health()
        
        # Recovery alerts
        if postgres_master_healthy and not self.last_postgres_master_up:
            self.alert_manager.send_recovery_alert(
                "✅ PostgreSQL Master Recovered",
                f"PostgreSQL master is now responding normally at {datetime.now()}"
            )
            self.last_postgres_master_up = True
        
        if redis_master_healthy and not self.last_redis_master_up:
            self.alert_manager.send_recovery_alert(
                "✅ Redis Master Recovered",
                f"Redis master is now responding normally at {datetime.now()}"
            )
            self.last_redis_master_up = True
        
        # Overall system health summary
        total_healthy = sum([
            postgres_master_healthy,
            postgres_replica_healthy,
            redis_master_healthy,
            healthy_sentinels >= 2
        ])
        
        if total_healthy < 3:  # If less than 3 components are healthy
            self.alert_manager.send_critical_alert(
                "🔥 CRITICAL: Database Infrastructure Degraded",
                f"Multiple database components are failing!\n"
                f"PostgreSQL Master: {'✅' if postgres_master_healthy else '❌'}\n"
                f"PostgreSQL Replica: {'✅' if postgres_replica_healthy else '❌'}\n"
                f"Redis Master: {'✅' if redis_master_healthy else '❌'}\n"
                f"Redis Sentinels: {'✅' if healthy_sentinels >= 2 else '❌'} ({healthy_sentinels}/3)\n"
                f"Immediate attention required!"
            )
        
        logger.info(f"Health check completed - {total_healthy}/4 components healthy")
    
    def start_monitoring(self):
        """Start the monitoring system"""
        # Start Prometheus metrics server
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")
        
        # Schedule regular health checks
        schedule.every(self.monitoring_interval).seconds.do(self.run_health_checks)
        
        # Initial startup alert
        self.alert_manager.send_info_alert(
            "🟢 Database Monitoring Started",
            f"Enterprise database monitoring system is now active.\n"
            f"Monitoring interval: {self.monitoring_interval} seconds\n"
            f"Targets: {self.postgres_master_host}, {self.postgres_replica_host}, {self.redis_master_host}"
        )
        
        # Run initial check
        self.run_health_checks()
        
        # Start monitoring loop
        logger.info("Starting monitoring loop...")
        while True:
            schedule.run_pending()
            time.sleep(1)

if __name__ == "__main__":
    monitor = DatabaseMonitor()
    monitor.start_monitoring()