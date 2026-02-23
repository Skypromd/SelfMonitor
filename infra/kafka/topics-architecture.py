"""
SelfMonitor Event Streaming Architecture - Kafka Topics Design
Production-ready event-driven architecture for 23 microservices
"""

# ================================================================================
#                        KAFKA TOPICS ARCHITECTURE
# ================================================================================

KAFKA_TOPICS = {
    # ===== USER LIFECYCLE EVENTS =====
    "user.lifecycle": {
        "partitions": 12,  # High throughput for user events
        "replication_factor": 3,
        "retention_ms": 2592000000,  # 30 days
        "cleanup_policy": "delete",
        "events": [
            "user.registered",
            "user.onboarded", 
            "user.profile_updated",
            "user.subscription_changed",
            "user.deleted"
        ]
    },
    
    # ===== AUTHENTICATION & SECURITY =====
    "auth.events": {
        "partitions": 6,
        "replication_factor": 3, 
        "retention_ms": 7776000000,  # 90 days (security audit)
        "cleanup_policy": "delete",
        "events": [
            "auth.login_attempt",
            "auth.login_success",
            "auth.login_failed", 
            "auth.logout",
            "auth.password_reset",
            "auth.mfa_enabled",
            "auth.suspicious_activity"
        ]
    },
    
    # ===== FINANCIAL TRANSACTIONS =====
    "transactions.stream": {
        "partitions": 24,  # Very high throughput
        "replication_factor": 3,
        "retention_ms": 31536000000,  # 365 days (financial records)
        "cleanup_policy": "delete",
        "events": [
            "transaction.created",
            "transaction.processed",
            "transaction.failed",
            "transaction.categorized",
            "transaction.reconciled"
        ]
    },
    
    # ===== AI & MACHINE LEARNING =====
    "ai.predictions": {
        "partitions": 8,
        "replication_factor": 3,
        "retention_ms": 2592000000,  # 30 days
        "cleanup_policy": "delete", 
        "events": [
            "prediction.generated",
            "prediction.served",
            "prediction.feedback",
            "model.retrained",
            "churn.prediction_updated"
        ]
    },
    
    # ===== FRAUD DETECTION =====
    "fraud.alerts": {
        "partitions": 6,
        "replication_factor": 3,
        "retention_ms": 7776000000,  # 90 days (compliance)
        "cleanup_policy": "delete",
        "events": [
            "fraud.risk_calculated",
            "fraud.alert_raised",
            "fraud.investigation_started",
            "fraud.case_resolved",
            "fraud.pattern_detected"
        ]
    },
    
    # ===== ANALYTICS & BUSINESS INTELLIGENCE =====
    "analytics.metrics": {
        "partitions": 16,  # High volume analytics
        "replication_factor": 3,
        "retention_ms": 7776000000,  # 90 days
        "cleanup_policy": "delete",
        "events": [
            "metric.calculated",
            "dashboard.viewed",
            "report.generated",
            "kpi.threshold_breached",
            "cohort.analysis_completed"
        ]
    },
    
    # ===== DOCUMENT PROCESSING =====
    "documents.lifecycle": {
        "partitions": 4,
        "replication_factor": 3,
        "retention_ms": 15552000000,  # 180 days
        "cleanup_policy": "delete",
        "events": [
            "document.uploaded",
            "document.processed",
            "document.classified",
            "document.extracted",
            "document.archived"
        ]
    },
    
    # ===== NOTIFICATIONS & COMMUNICATION =====
    "notifications.outbound": {
        "partitions": 8,
        "replication_factor": 3,
        "retention_ms": 2592000000,  # 30 days
        "cleanup_policy": "delete",
        "events": [
            "notification.triggered",
            "email.sent",
            "sms.sent", 
            "push.sent",
            "notification.read"
        ]
    },
    
    # ===== COMPLIANCE & AUDIT =====
    "compliance.audit": {
        "partitions": 4,
        "replication_factor": 3,
        "retention_ms": 157680000000,  # 5 years (regulatory requirement)
        "cleanup_policy": "delete",
        "events": [
            "audit.log_created",
            "compliance.check_performed",
            "regulation.violation_detected",
            "data.access_logged",
            "consent.updated"
        ]
    },
    
    # ===== INTEGRATIONS & EXTERNAL APIs =====
    "integrations.external": {
        "partitions": 6,
        "replication_factor": 3,
        "retention_ms": 2592000000,  # 30 days
        "cleanup_policy": "delete",
        "events": [
            "api.call_made",
            "api.response_received",
            "webhook.received",
            "sync.completed",
            "integration.error"
        ]
    },
    
    # ===== SYSTEM MONITORING =====
    "system.monitoring": {
        "partitions": 12,
        "replication_factor": 3,
        "retention_ms": 604800000,  # 7 days (operational data)
        "cleanup_policy": "delete",
        "events": [
            "service.health_check",
            "performance.metric",
            "error.occurred",
            "alert.triggered",
            "system.resource_usage"
        ]
    }
}

# ================================================================================
#                        EVENT SCHEMAS (Avro Format)
# ================================================================================

AVRO_SCHEMAS = {
    
    "user.registered": {
        "type": "record",
        "name": "UserRegistered", 
        "namespace": "com.selfmonitor.events.user",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}},
            {"name": "user_id", "type": "string"},
            {"name": "email", "type": "string"},
            {"name": "account_type", "type": {"type": "enum", "symbols": ["personal", "business", "enterprise"]}},
            {"name": "registration_source", "type": ["null", "string"], "default": None},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    },
    
    "transaction.created": {
        "type": "record", 
        "name": "TransactionCreated",
        "namespace": "com.selfmonitor.events.transactions",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}},
            {"name": "transaction_id", "type": "string"},
            {"name": "user_id", "type": "string"},
            {"name": "amount", "type": {"type": "bytes", "logicalType": "decimal", "precision": 10, "scale": 2}},
            {"name": "currency", "type": "string"},
            {"name": "description", "type": ["null", "string"], "default": None},
            {"name": "category", "type": ["null", "string"], "default": None},
            {"name": "merchant", "type": ["null", "string"], "default": None},
            {"name": "account_id", "type": "string"},
            {"name": "transaction_type", "type": {"type": "enum", "symbols": ["debit", "credit", "transfer"]}},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    },
    
    "fraud.alert_raised": {
        "type": "record",
        "name": "FraudAlertRaised", 
        "namespace": "com.selfmonitor.events.fraud",
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}},
            {"name": "alert_id", "type": "string"},
            {"name": "user_id", "type": "string"},
            {"name": "transaction_id", "type": ["null", "string"], "default": None},
            {"name": "risk_score", "type": "float"},
            {"name": "risk_factors", "type": {"type": "array", "items": "string"}},
            {"name": "alert_type", "type": {"type": "enum", "symbols": ["velocity", "pattern", "location", "amount", "behavior"]}},
            {"name": "severity", "type": {"type": "enum", "symbols": ["low", "medium", "high", "critical"]}},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    },
    
    "ai.prediction_generated": {
        "type": "record",
        "name": "AIPredictionGenerated",
        "namespace": "com.selfmonitor.events.ai", 
        "fields": [
            {"name": "event_id", "type": "string"},
            {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}},
            {"name": "prediction_id", "type": "string"},
            {"name": "user_id", "type": "string"},
            {"name": "model_name", "type": "string"},
            {"name": "model_version", "type": "string"},
            {"name": "prediction_type", "type": {"type": "enum", "symbols": ["recommendation", "churn", "fraud", "categorization", "optimization"]}},
            {"name": "confidence_score", "type": "float"},
            {"name": "prediction_data", "type": {"type": "map", "values": "string"}},
            {"name": "features_used", "type": {"type": "array", "items": "string"}},
            {"name": "metadata", "type": {"type": "map", "values": "string"}}
        ]
    }
}

# ================================================================================
#                        CONSUMER GROUPS CONFIGURATION
# ================================================================================

CONSUMER_GROUPS = {
    
    # Real-time processing groups
    "fraud-detection-realtime": {
        "topics": ["transactions.stream", "auth.events"],
        "processing_type": "real-time",
        "max_poll_records": 100,
        "auto_commit_interval": 1000
    },
    
    "ai-predictions-realtime": {
        "topics": ["user.lifecycle", "transactions.stream", "analytics.metrics"],
        "processing_type": "real-time", 
        "max_poll_records": 50,
        "auto_commit_interval": 1000
    },
    
    # Batch processing groups
    "analytics-batch": {
        "topics": ["transactions.stream", "user.lifecycle", "ai.predictions"],
        "processing_type": "batch",
        "max_poll_records": 1000,
        "auto_commit_interval": 5000
    },
    
    "compliance-audit": {
        "topics": ["auth.events", "compliance.audit", "fraud.alerts"],
        "processing_type": "batch",
        "max_poll_records": 500, 
        "auto_commit_interval": 10000
    },
    
    # Dead letter queue processing
    "dlq-processor": {
        "topics": ["*.dlq"],
        "processing_type": "error-handling",
        "max_poll_records": 10,
        "auto_commit_interval": 30000
    }
}

# ================================================================================
#                        KAFKA STREAMS TOPOLOGY
# ================================================================================

STREAM_PROCESSING_TOPOLOGIES = {
    
    "user-transaction-enrichment": {
        "input_topics": ["transactions.stream", "user.lifecycle"],
        "output_topic": "transactions.enriched",
        "processing_logic": "join transactions with user profile data",
        "state_stores": ["user-profiles-store"],
        "window_duration_ms": 300000  # 5 minutes
    },
    
    "real-time-fraud-scoring": {
        "input_topics": ["transactions.stream", "auth.events"],
        "output_topic": "fraud.alerts",
        "processing_logic": "calculate fraud risk scores in real-time",
        "state_stores": ["user-behavior-store", "transaction-patterns-store"],
        "window_duration_ms": 600000  # 10 minutes  
    },
    
    "churn-prediction-aggregation": {
        "input_topics": ["user.lifecycle", "analytics.metrics", "ai.predictions"],
        "output_topic": "churn.predictions",
        "processing_logic": "aggregate user behavior for churn prediction",
        "state_stores": ["user-activity-store"],
        "window_duration_ms": 86400000  # 24 hours
    }
}

# ================================================================================
#                        MONITORING & ALERTING
# ================================================================================

MONITORING_CONFIG = {
    "lag_threshold": 1000,  # Alert if consumer lag > 1000 messages
    "throughput_threshold": 10000,  # Alert if throughput < 10k msgs/sec
    "error_rate_threshold": 0.05,  # Alert if error rate > 5%
    "partition_distribution_check": True,
    "consumer_group_health_check": True,
    "broker_health_check": True
}

if __name__ == "__main__":
    print("SelfMonitor Kafka Event Streaming Architecture")
    print(f"Total Topics: {len(KAFKA_TOPICS)}")
    print(f"Total Consumer Groups: {len(CONSUMER_GROUPS)}")
    print(f"Stream Processing Topologies: {len(STREAM_PROCESSING_TOPOLOGIES)}")
    
    # Calculate total partitions
    total_partitions = sum(topic["partitions"] for topic in KAFKA_TOPICS.values())
    print(f"Total Partitions: {total_partitions}")
    
    # Show topic distribution
    print("\nTopic Distribution:")
    for name, config in KAFKA_TOPICS.items():
        print(f"  {name}: {config['partitions']} partitions, {config['retention_ms']//86400000} days retention")