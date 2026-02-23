#!/usr/bin/env python3
"""
Kafka Topics Setup and Migration Script for SelfMonitor
Automated topic creation and Redis Streams migration
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
    from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
    from kafka.errors import TopicAlreadyExistsError
    kafka_available = True
except ImportError:
    print("⚠️  kafka-python not available. Install with: pip install kafka-python")
    kafka_available = False

try:
    import redis
    redis_available = True
except ImportError:
    print("⚠️  redis not available. Install with: pip install redis")
    redis_available = False

from topics_architecture import KAFKA_TOPICS, CONSUMER_GROUPS, AVRO_SCHEMAS

class KafkaSetupManager:
    """Manage Kafka cluster setup and topic creation"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = None
        self.producer = None
        
        if kafka_available:
            try:
                self.admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
                self.producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                    key_serializer=lambda x: x.encode('utf-8') if x else None
                )
                print(f"✓ Connected to Kafka at {bootstrap_servers}")
            except Exception as e:
                print(f"❌ Failed to connect to Kafka: {e}")
                self.admin_client = None
                self.producer = None
    
    def create_topics(self) -> bool:
        """Create all SelfMonitor Kafka topics"""
        if not self.admin_client:
            print("❌ Kafka admin client not available")
            return False
            
        print("🚀 Creating Kafka topics...")
        
        # Convert our topic configuration to Kafka NewTopic format
        topics_to_create = []
        
        for topic_name, config in KAFKA_TOPICS.items():
            topic = NewTopic(
                name=topic_name,
                num_partitions=config["partitions"],
                replication_factor=min(config["replication_factor"], 1),  # Single broker for dev
                topic_configs={
                    "retention.ms": str(config["retention_ms"]),
                    "cleanup.policy": config["cleanup_policy"],
                    "compression.type": "snappy",  # Better performance
                    "min.insync.replicas": "1"
                }
            )
            topics_to_create.append(topic)
        
        try:
            # Create topics
            future_results = self.admin_client.create_topics(topics_to_create, validate_only=False)
            
            # Wait for creation results
            created_count = 0
            failed_count = 0
            
            for topic_name, future in future_results.items():
                try:
                    future.result(timeout=30)
                    print(f"  ✓ Created topic: {topic_name}")
                    created_count += 1
                except TopicAlreadyExistsError:
                    print(f"  ⚠️  Topic already exists: {topic_name}")  
                    created_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to create topic {topic_name}: {e}")
                    failed_count += 1
            
            print(f"\n📊 Topic creation summary:")
            print(f"  ✓ Created/Verified: {created_count}")
            print(f"  ❌ Failed: {failed_count}")
            
            return failed_count == 0
            
        except Exception as e:
            print(f"❌ Bulk topic creation failed: {e}")
            return False
    
    def verify_topics(self) -> Dict[str, Any]:
        """Verify all topics are created correctly"""
        if not self.admin_client:
            return {"error": "Admin client not available"}
            
        try:
            # Get topic metadata
            metadata = self.producer.list_topics(timeout=10)
            existing_topics = set(metadata.topics.keys())
            expected_topics = set(KAFKA_TOPICS.keys())
            
            missing_topics = expected_topics - existing_topics
            extra_topics = existing_topics - expected_topics
            
            # Get topic configurations
            topic_configs = {}
            for topic_name in expected_topics.intersection(existing_topics):
                try:
                    config_resource = ConfigResource(ConfigResourceType.TOPIC, topic_name)
                    configs = self.admin_client.describe_configs([config_resource])
                    topic_configs[topic_name] = configs[config_resource].result()
                except Exception as e:
                    topic_configs[topic_name] = {"error": str(e)}
            
            return {
                "total_expected": len(expected_topics),
                "total_existing": len(existing_topics),
                "missing_topics": list(missing_topics),
                "extra_topics": list(extra_topics),
                "configurations": topic_configs,
                "status": "healthy" if not missing_topics else "incomplete"
            }
            
        except Exception as e:
            return {"error": f"Topic verification failed: {e}"}

class RedisStreamsMigrator:
    """Migrate data from Redis Streams to Kafka topics"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = None
        self.migration_stats = {}
        
        if redis_available:
            try:
                self.redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
                self.redis_client.ping()
                print(f"✓ Connected to Redis at {redis_host}:{redis_port}")
            except Exception as e:
                print(f"❌ Failed to connect to Redis: {e}")
                self.redis_client = None
    
    async def discover_streams(self) -> List[str]:
        """Discover existing Redis streams that need migration"""
        if not self.redis_client:
            return []
            
        try:
            # Look for common stream patterns  
            stream_patterns = [
                "user:*", "transaction:*", "auth:*", "fraud:*", 
                "analytics:*", "notification:*", "document:*"
            ]
            
            discovered_streams = []
            for pattern in stream_patterns:
                keys = self.redis_client.keys(pattern)
                for key in keys:
                    if self.redis_client.type(key) == 'stream':
                        discovered_streams.append(key)
            
            print(f"🔍 Discovered {len(discovered_streams)} Redis streams")
            return discovered_streams
            
        except Exception as e:
            print(f"❌ Stream discovery failed: {e}")
            return []
    
    async def migrate_stream_to_topic(self, stream_name: str, topic_name: str, kafka_producer, batch_size: int = 1000):
        """Migrate specific Redis stream to Kafka topic"""
        if not self.redis_client or not kafka_producer:
            return {"error": "Clients not available"}
            
        try:
            print(f"🔄 Migrating {stream_name} → {topic_name}")
            
            # Read all messages from stream
            messages = self.redis_client.xrange(stream_name, count=batch_size)
            migrated_count = 0
            
            for message_id, fields in messages:
                try:
                    # Convert Redis stream message to Kafka format
                    kafka_message = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "source_stream": stream_name,
                        "original_id": message_id,
                        "data": fields
                    }
                    
                    # Send to Kafka
                    future = kafka_producer.send(topic_name, value=kafka_message)
                    future.get(timeout=10)  # Wait for acknowledgment
                    migrated_count += 1
                    
                except Exception as e:
                    print(f"  ❌ Failed to migrate message {message_id}: {e}")
            
            self.migration_stats[stream_name] = {
                "target_topic": topic_name,
                "messages_migrated": migrated_count,
                "total_messages": len(messages),
                "success_rate": migrated_count / len(messages) if messages else 1.0
            }
            
            print(f"  ✓ Migrated {migrated_count}/{len(messages)} messages")
            return self.migration_stats[stream_name]
            
        except Exception as e:
            print(f"❌ Migration failed for {stream_name}: {e}")
            return {"error": str(e)}

async def main():
    """Main setup and migration function"""
    print("="*80)
    print("               🚀 SelfMonitor Kafka Setup & Migration")  
    print("="*80)
    
    # Initialize managers
    kafka_manager = KafkaSetupManager()
    redis_migrator = RedisStreamsMigrator()
    
    # Step 1: Create Kafka topics
    print("\n📋 Step 1: Creating Kafka topics...")
    if kafka_manager.admin_client:
        success = kafka_manager.create_topics()
        if success:
            print("✅ All topics created successfully")
        else:
            print("❌ Some topics failed to create")
            
        # Verify topics
        print("\n🔍 Verifying topic configuration...")
        verification = kafka_manager.verify_topics()
        print(f"Topics status: {verification.get('status', 'unknown')}")
        
        if verification.get('missing_topics'):
            print(f"Missing topics: {verification['missing_topics']}")
        
    else:
        print("⚠️  Kafka not available - skipping topic creation")
    
    # Step 2: Discover Redis streams
    print("\n📋 Step 2: Discovering Redis streams...")
    streams = await redis_migrator.discover_streams()
    
    if streams:
        print(f"Found streams: {streams}")
        
        # Step 3: Migrate streams to topics
        print("\n📋 Step 3: Migrating Redis streams to Kafka...")
        
        # Define stream to topic mappings
        stream_mappings = {
            "user:events": "user.lifecycle",
            "transaction:stream": "transactions.stream", 
            "auth:events": "auth.events",
            "fraud:alerts": "fraud.alerts",
            "analytics:events": "analytics.metrics"
        }
        
        for stream_name in streams:
            # Find appropriate topic mapping
            target_topic = None
            for pattern, topic in stream_mappings.items():
                if pattern in stream_name or stream_name.startswith(pattern.split(':')[0]):
                    target_topic = topic
                    break
            
            if target_topic and kafka_manager.producer:
                await redis_migrator.migrate_stream_to_topic(
                    stream_name, target_topic, kafka_manager.producer
                )
            else:
                print(f"⚠️  No topic mapping found for stream: {stream_name}")
    
    else:
        print("ℹ️  No Redis streams found - creating sample events...")
        
        # Create sample events for testing
        if kafka_manager.producer:
            sample_events = [
                ("user.lifecycle", {"event": "user.registered", "user_id": "test_123", "email": "test@selfmonitor.com"}),
                ("transactions.stream", {"event": "transaction.created", "user_id": "test_123", "amount": 150.00}),
                ("ai.predictions", {"event": "prediction.generated", "user_id": "test_123", "confidence": 0.92})
            ]
            
            for topic, event in sample_events:
                try:
                    kafka_manager.producer.send(topic, value=event)
                    print(f"  ✓ Sent sample event to {topic}")
                except Exception as e:
                    print(f"  ❌ Failed to send to {topic}: {e}")
    
    # Step 4: Display migration summary
    print("\n📊 Migration Summary:")
    if redis_migrator.migration_stats:
        for stream, stats in redis_migrator.migration_stats.items():
            success_rate = stats.get('success_rate', 0) * 100
            print(f"  {stream} → {stats['target_topic']}: {success_rate:.1f}% success")
    else:
        print("  No migrations performed")
    
    # Step 5: Setup consumer groups
    print("\n📋 Step 4: Consumer group recommendations:")
    for group_name, config in CONSUMER_GROUPS.items():
        topics = ", ".join(config["topics"])
        print(f"  {group_name}: {topics}")
        print(f"    Type: {config['processing_type']}")
        print(f"    Max poll: {config['max_poll_records']} records")
    
    print(f"\n✅ Kafka setup completed!")
    print(f"🌐 Management UI: http://localhost:8080")
    print(f"📊 Topics configured: {len(KAFKA_TOPICS)}")
    print(f"🔄 Consumer groups defined: {len(CONSUMER_GROUPS)}")
    
    print(f"\nNext steps:")
    print(f"1. Update microservices to use Kafka producers")
    print(f"2. Implement Kafka consumers for real-time processing")
    print(f"3. Set up monitoring and alerting")
    print(f"4. Configure schema registry for Avro schemas")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()