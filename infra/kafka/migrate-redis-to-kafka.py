#!/usr/bin/env python3
"""
SelfMonitor Redis Streams to Kafka Migration
Production-ready data migration from Redis Streams to Apache Kafka
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import redis
import asyncio_redis
from kafka import KafkaProducer
from kafka.errors import KafkaError
from avro import schema, io as avro_io
import io
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class MigrationConfig:
    """Configuration for Redis to Kafka migration"""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    kafka_bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8081"
    batch_size: int = 1000
    parallel_workers: int = 4
    dry_run: bool = False
    include_streams: Optional[List[str]] = None
    exclude_streams: Optional[List[str]] = None

@dataclass
class StreamMapping:
    """Mapping between Redis streams and Kafka topics"""
    redis_stream: str
    kafka_topic: str
    event_type_field: str = "event_type"
    schema_name: str = None

class AvroEventSerializer:
    """Avro serializer for Kafka events"""
    
    def __init__(self, schema_registry_url: str):
        self.schema_registry_url = schema_registry_url
        self.schemas = {}
        self.load_schemas()
    
    def load_schemas(self):
        """Load Avro schemas for event serialization"""
        self.schemas = {
            "user.events": {
                "type": "record",
                "name": "UserEvent",
                "namespace": "com.selfmonitor.events.user",
                "fields": [
                    {"name": "event_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "user_id", "type": ["null", "string"], "default": None},
                    {"name": "timestamp", "type": "long"},
                    {"name": "source_service", "type": "string"},
                    {"name": "correlation_id", "type": ["null", "string"], "default": None},
                    {"name": "data", "type": "string"},
                    {"name": "metadata", "type": {"type": "map", "values": "string"}, "default": {}}
                ]
            },
            "transaction.events": {
                "type": "record",
                "name": "TransactionEvent",
                "namespace": "com.selfmonitor.events.transaction",
                "fields": [
                    {"name": "event_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "transaction_id", "type": "string"},
                    {"name": "user_id", "type": "string"},
                    {"name": "amount", "type": "double"},
                    {"name": "currency", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "source_service", "type": "string"},
                    {"name": "correlation_id", "type": ["null", "string"], "default": None},
                    {"name": "data", "type": "string"},
                    {"name": "metadata", "type": {"type": "map", "values": "string"}, "default": {}}
                ]
            },
            "fraud.alerts": {
                "type": "record",
                "name": "FraudAlert",
                "namespace": "com.selfmonitor.events.fraud",
                "fields": [
                    {"name": "event_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "alert_id", "type": "string"},
                    {"name": "user_id", "type": "string"},
                    {"name": "risk_score", "type": "double"},
                    {"name": "alert_level", "type": {"type": "enum", "name": "AlertLevel", "symbols": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}},
                    {"name": "timestamp", "type": "long"},
                    {"name": "source_service", "type": "string"},
                    {"name": "correlation_id", "type": ["null", "string"], "default": None},
                    {"name": "data", "type": "string"},
                    {"name": "metadata", "type": {"type": "map", "values": "string"}, "default": {}}
                ]
            },
            "analytics.events": {
                "type": "record",
                "name": "AnalyticsEvent",
                "namespace": "com.selfmonitor.events.analytics",
                "fields": [
                    {"name": "event_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "user_id", "type": ["null", "string"], "default": None},
                    {"name": "session_id", "type": ["null", "string"], "default": None},
                    {"name": "metric_name", "type": "string"},
                    {"name": "metric_value", "type": "double"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "source_service", "type": "string"},
                    {"name": "correlation_id", "type": ["null", "string"], "default": None},
                    {"name": "data", "type": "string"},
                    {"name": "metadata", "type": {"type": "map", "values": "string"}, "default": {}}
                ]
            },
            "audit.events": {
                "type": "record",
                "name": "AuditEvent",
                "namespace": "com.selfmonitor.events.audit",
                "fields": [
                    {"name": "event_id", "type": "string"},
                    {"name": "event_type", "type": "string"},
                    {"name": "user_id", "type": ["null", "string"], "default": None},
                    {"name": "resource_type", "type": "string"},
                    {"name": "resource_id", "type": "string"},
                    {"name": "action", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "source_service", "type": "string"},
                    {"name": "correlation_id", "type": ["null", "string"], "default": None},
                    {"name": "data", "type": "string"},
                    {"name": "metadata", "type": {"type": "map", "values": "string"}, "default": {}}
                ]
            }
        }
    
    def get_schema(self, topic: str) -> schema.Schema:
        """Get Avro schema for topic"""
        if topic not in self.schemas:
            raise ValueError(f"No schema found for topic: {topic}")
        return schema.parse(json.dumps(self.schemas[topic]))
    
    def serialize(self, topic: str, event_data: Dict[str, Any]) -> bytes:
        """Serialize event data to Avro format"""
        try:
            avro_schema = self.get_schema(topic)
            
            # Create Avro writer
            writer = avro_io.DatumWriter(avro_schema)
            bytes_writer = io.BytesIO()
            encoder = avro_io.BinaryEncoder(bytes_writer)
            
            # Write data
            writer.write(event_data, encoder)
            
            return bytes_writer.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to serialize event for topic {topic}: {str(e)}")
            logger.error(f"Event data: {event_data}")
            raise

class RedisStreamReader:
    """Redis Streams reader for migration"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.redis_client = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await asyncio_redis.Connection.create(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db
            )
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def get_streams(self) -> List[str]:
        """Get list of Redis streams to migrate"""
        try:
            # Get all keys that look like streams
            all_keys = await self.redis_client.keys("*")
            streams = []
            
            for key in all_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                # Check if it's a stream by trying to get stream info
                try:
                    await self.redis_client.xinfo_stream(key_str)
                    streams.append(key_str)
                except:
                    continue
            
            # Filter streams based on configuration
            if self.config.include_streams:
                streams = [s for s in streams if s in self.config.include_streams]
            
            if self.config.exclude_streams:
                streams = [s for s in streams if s not in self.config.exclude_streams]
            
            logger.info(f"Found {len(streams)} streams to migrate: {streams}")
            return streams
            
        except Exception as e:
            logger.error(f"Failed to get Redis streams: {str(e)}")
            raise
    
    async def read_stream_messages(self, stream_name: str, start_id: str = "0") -> List[Dict]:
        """Read all messages from a Redis stream"""
        try:
            messages = []
            current_id = start_id
            
            while True:
                # Read batch of messages
                result = await self.redis_client.xread([stream_name], [current_id], count=self.config.batch_size)
                
                if not result or stream_name.encode() not in result:
                    break
                
                stream_messages = result[stream_name.encode()]
                if not stream_messages:
                    break
                
                batch_messages = []
                for msg_id, fields in stream_messages:
                    # Convert Redis message to event format
                    message_data = {
                        "stream_id": msg_id.decode(),
                        "stream_name": stream_name,
                        "fields": {}
                    }
                    
                    # Decode field data
                    for field_name, field_value in fields.items():
                        key = field_name.decode() if isinstance(field_name, bytes) else field_name
                        value = field_value.decode() if isinstance(field_value, bytes) else field_value
                        
                        # Try to parse JSON values
                        try:
                            message_data["fields"][key] = json.loads(value)
                        except:
                            message_data["fields"][key] = value
                    
                    batch_messages.append(message_data)
                    current_id = msg_id.decode()
                
                messages.extend(batch_messages)
                logger.info(f"Read {len(batch_messages)} messages from {stream_name} (total: {len(messages)})")
                
                # If we got fewer messages than batch size, we're done
                if len(stream_messages) < self.config.batch_size:
                    break
            
            logger.info(f"Finished reading {len(messages)} messages from stream {stream_name}")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to read stream {stream_name}: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            self.redis_client.close()

class KafkaEventProducer:
    """Kafka producer for migration"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.producer = None
        self.serializer = AvroEventSerializer(config.schema_registry_url)
        self.stream_mappings = self.get_stream_mappings()
    
    def get_stream_mappings(self) -> Dict[str, StreamMapping]:
        """Get mapping between Redis streams and Kafka topics"""
        return {
            # User service streams
            "user_events": StreamMapping("user_events", "user.events"),
            "user:events": StreamMapping("user:events", "user.events"),
            "users:stream": StreamMapping("users:stream", "user.events"),
            
            # Transaction service streams
            "transaction_events": StreamMapping("transaction_events", "transaction.events"),
            "transaction:events": StreamMapping("transaction:events", "transaction.events"),
            "payments:stream": StreamMapping("payments:stream", "transaction.events"),
            
            # Fraud detection streams
            "fraud_alerts": StreamMapping("fraud_alerts", "fraud.alerts"),
            "fraud:alerts": StreamMapping("fraud:alerts", "fraud.alerts"),
            "risk:events": StreamMapping("risk:events", "fraud.alerts"),
            
            # Analytics streams
            "analytics_events": StreamMapping("analytics_events", "analytics.events"),
            "analytics:events": StreamMapping("analytics:events", "analytics.events"),
            "metrics:stream": StreamMapping("metrics:stream", "analytics.events"),
            
            # Audit streams
            "audit_events": StreamMapping("audit_events", "audit.events"),
            "audit:events": StreamMapping("audit:events", "audit.events"),
            "logs:stream": StreamMapping("logs:stream", "audit.events"),
            
            # Notification streams
            "notification_events": StreamMapping("notification_events", "notification.events"),
            "notifications:stream": StreamMapping("notifications:stream", "notification.events"),
            
            # Default mapping for unmapped streams
            "default": StreamMapping("default", "system.events")
        }
    
    def connect(self):
        """Connect to Kafka"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config.kafka_bootstrap_servers,
                value_serializer=None,  # We'll handle serialization manually
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                acks='all',
                retries=3,
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
                compression_type='snappy'
            )
            logger.info("Connected to Kafka")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {str(e)}")
            raise
    
    def transform_redis_message(self, redis_message: Dict, kafka_topic: str) -> Dict[str, Any]:
        """Transform Redis stream message to Kafka event format"""
        try:
            fields = redis_message["fields"]
            
            # Extract common fields
            event_id = fields.get("event_id", redis_message["stream_id"])
            event_type = fields.get("event_type", "unknown")
            timestamp = fields.get("timestamp", int(time.time() * 1000))
            
            # Convert timestamp to milliseconds if needed
            if isinstance(timestamp, str):
                try:
                    timestamp = int(float(timestamp) * 1000)
                except:
                    timestamp = int(time.time() * 1000)
            elif timestamp < 10**10:  # If timestamp is in seconds
                timestamp = timestamp * 1000
            
            # Base event structure
            event_data = {
                "event_id": str(event_id),
                "event_type": str(event_type),
                "timestamp": int(timestamp),
                "source_service": fields.get("source", "redis-migration"),
                "correlation_id": fields.get("correlation_id"),
                "data": json.dumps(fields),
                "metadata": {
                    "migrated_from_redis": "true",
                    "original_stream": redis_message["stream_name"],
                    "migration_timestamp": str(int(time.time() * 1000))
                }
            }
            
            # Add topic-specific fields
            if kafka_topic == "user.events":
                event_data["user_id"] = fields.get("user_id")
            elif kafka_topic == "transaction.events":
                event_data["transaction_id"] = fields.get("transaction_id", event_id)
                event_data["user_id"] = fields.get("user_id", "unknown")
                event_data["amount"] = float(fields.get("amount", 0.0))
                event_data["currency"] = fields.get("currency", "USD")
            elif kafka_topic == "fraud.alerts":
                event_data["alert_id"] = fields.get("alert_id", event_id)
                event_data["user_id"] = fields.get("user_id", "unknown")
                event_data["risk_score"] = float(fields.get("risk_score", 0.0))
                event_data["alert_level"] = fields.get("alert_level", "LOW").upper()
            elif kafka_topic == "analytics.events":
                event_data["user_id"] = fields.get("user_id")
                event_data["session_id"] = fields.get("session_id")
                event_data["metric_name"] = fields.get("metric_name", "unknown")
                event_data["metric_value"] = float(fields.get("metric_value", 0.0))
            elif kafka_topic == "audit.events":
                event_data["user_id"] = fields.get("user_id")
                event_data["resource_type"] = fields.get("resource_type", "unknown")
                event_data["resource_id"] = fields.get("resource_id", event_id)
                event_data["action"] = fields.get("action", "unknown")
            
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to transform Redis message: {str(e)}")
            logger.error(f"Redis message: {redis_message}")
            raise
    
    def get_kafka_topic(self, redis_stream: str) -> str:
        """Get Kafka topic for Redis stream"""
        mapping = self.stream_mappings.get(redis_stream)
        if mapping:
            return mapping.kafka_topic
        
        # Default mapping based on stream name patterns
        if "user" in redis_stream.lower():
            return "user.events"
        elif "transaction" in redis_stream.lower() or "payment" in redis_stream.lower():
            return "transaction.events"
        elif "fraud" in redis_stream.lower() or "risk" in redis_stream.lower():
            return "fraud.alerts"
        elif "analytics" in redis_stream.lower() or "metric" in redis_stream.lower():
            return "analytics.events"
        elif "audit" in redis_stream.lower() or "log" in redis_stream.lower():
            return "audit.events"
        elif "notification" in redis_stream.lower():
            return "notification.events"
        else:
            return "system.events"
    
    def produce_message(self, kafka_topic: str, event_data: Dict[str, Any]) -> bool:
        """Produce single message to Kafka"""
        try:
            if self.config.dry_run:
                logger.info(f"[DRY RUN] Would produce to {kafka_topic}: {event_data['event_type']}")
                return True
            
            # Serialize with Avro
            serialized_value = self.serializer.serialize(kafka_topic, event_data)
            
            # Use event_id as key for partitioning
            key = event_data.get("event_id")
            
            # Send to Kafka
            self.producer.send(
                topic=kafka_topic,
                key=key,
                value=serialized_value
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to produce message to {kafka_topic}: {str(e)}")
            logger.error(f"Event data: {event_data}")
            return False
    
    def disconnect(self):
        """Disconnect from Kafka"""
        if self.producer:
            self.producer.flush()
            self.producer.close()

class MigrationStats:
    """Migration statistics tracking"""
    
    def __init__(self):
        self.start_time = time.time()
        self.total_streams = 0
        self.processed_streams = 0
        self.total_messages = 0
        self.successful_messages = 0
        self.failed_messages = 0
        self.messages_per_topic = {}
        self.errors = []
    
    def add_stream(self):
        """Add stream to statistics"""
        self.total_streams += 1
    
    def complete_stream(self):
        """Mark stream as completed"""
        self.processed_streams += 1
    
    def add_message_success(self, topic: str):
        """Add successful message"""
        self.total_messages += 1
        self.successful_messages += 1
        self.messages_per_topic[topic] = self.messages_per_topic.get(topic, 0) + 1
    
    def add_message_failure(self, topic: str, error: str):
        """Add failed message"""
        self.total_messages += 1
        self.failed_messages += 1
        self.errors.append({
            "topic": topic,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Get migration summary"""
        duration = time.time() - self.start_time
        return {
            "duration_seconds": round(duration, 2),
            "total_streams": self.total_streams,
            "processed_streams": self.processed_streams,
            "total_messages": self.total_messages,
            "successful_messages": self.successful_messages,
            "failed_messages": self.failed_messages,
            "success_rate": round(self.successful_messages / max(self.total_messages, 1) * 100, 2),
            "messages_per_second": round(self.successful_messages / max(duration, 1), 2),
            "messages_per_topic": self.messages_per_topic,
            "errors": self.errors[-10:]  # Last 10 errors
        }

class RedisToKafkaMigrator:
    """Main migration class"""
    
    def __init__(self, config: MigrationConfig):
        self.config = config
        self.redis_reader = RedisStreamReader(config)
        self.kafka_producer = KafkaEventProducer(config)
        self.stats = MigrationStats()
    
    async def migrate_stream(self, stream_name: str) -> bool:
        """Migrate single Redis stream to Kafka"""
        try:
            logger.info(f"Starting migration of stream: {stream_name}")
            
            # Read all messages from Redis stream
            messages = await self.redis_reader.read_stream_messages(stream_name)
            
            if not messages:
                logger.info(f"No messages found in stream {stream_name}")
                return True
            
            # Get target Kafka topic
            kafka_topic = self.kafka_producer.get_kafka_topic(stream_name)
            logger.info(f"Migrating {len(messages)} messages from {stream_name} to {kafka_topic}")
            
            # Process messages in batches
            batch_size = self.config.batch_size
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i+batch_size]
                
                for message in batch:
                    try:
                        # Transform Redis message to Kafka event
                        event_data = self.kafka_producer.transform_redis_message(message, kafka_topic)
                        
                        # Produce to Kafka
                        success = self.kafka_producer.produce_message(kafka_topic, event_data)
                        
                        if success:
                            self.stats.add_message_success(kafka_topic)
                        else:
                            self.stats.add_message_failure(kafka_topic, "Production failed")
                            
                    except Exception as e:
                        error_msg = f"Failed to process message: {str(e)}"
                        logger.error(error_msg)
                        self.stats.add_message_failure(kafka_topic, error_msg)
                
                # Log progress
                processed = min(i + batch_size, len(messages))
                logger.info(f"Processed {processed}/{len(messages)} messages from {stream_name}")
            
            self.stats.complete_stream()
            logger.info(f"Completed migration of stream {stream_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate stream {stream_name}: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    async def migrate_all_streams(self):
        """Migrate all Redis streams to Kafka"""
        try:
            logger.info("Starting Redis to Kafka migration")
            
            # Connect to Redis and Kafka
            await self.redis_reader.connect()
            self.kafka_producer.connect()
            
            # Get list of streams to migrate
            streams = await self.redis_reader.get_streams()
            
            if not streams:
                logger.info("No streams found to migrate")
                return
            
            for stream in streams:
                self.stats.add_stream()
            
            # Migrate streams in parallel
            if self.config.parallel_workers > 1:
                semaphore = asyncio.Semaphore(self.config.parallel_workers)
                
                async def migrate_with_semaphore(stream_name):
                    async with semaphore:
                        return await self.migrate_stream(stream_name)
                
                tasks = [migrate_with_semaphore(stream) for stream in streams]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log any failed migrations
                for stream, result in zip(streams, results):
                    if isinstance(result, Exception):
                        logger.error(f"Stream {stream} migration failed: {str(result)}")
            else:
                # Sequential migration
                for stream in streams:
                    await self.migrate_stream(stream)
            
            # Print final statistics
            summary = self.stats.get_summary()
            logger.info("Migration completed!")
            logger.info(f"Summary: {json.dumps(summary, indent=2)}")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        
        finally:
            # Cleanup connections
            await self.redis_reader.disconnect()
            self.kafka_producer.disconnect()

def main():
    """Main migration script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate Redis Streams to Kafka")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--redis-db", type=int, default=0, help="Redis database")
    parser.add_argument("--kafka-bootstrap", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--schema-registry", default="http://localhost:8081", help="Schema Registry URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--include-streams", nargs='+', help="Streams to include")
    parser.add_argument("--exclude-streams", nargs='+', help="Streams to exclude")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create configuration
    config = MigrationConfig(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_db=args.redis_db,
        kafka_bootstrap_servers=args.kafka_bootstrap,
        schema_registry_url=args.schema_registry,
        batch_size=args.batch_size,
        parallel_workers=args.workers,
        dry_run=args.dry_run,
        include_streams=args.include_streams,
        exclude_streams=args.exclude_streams
    )
    
    # Run migration
    migrator = RedisToKafkaMigrator(config)
    
    try:
        asyncio.run(migrator.migrate_all_streams())
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()