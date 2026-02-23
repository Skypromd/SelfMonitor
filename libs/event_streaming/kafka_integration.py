"""
SelfMonitor Kafka Integration Library
Production-ready event streaming for microservices
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.errors import KafkaError
    kafka_available = True
except ImportError:
    kafka_available = False

try:
    import redis
    redis_available = True  
except ImportError:
    redis_available = False

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class EventMetadata:
    """Standard metadata for all events"""
    event_id: str
    timestamp: str
    service_name: str
    event_type: str
    version: str = "1.0"
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None

@dataclass 
class SelfMonitorEvent:
    """Standard event structure for SelfMonitor platform"""
    metadata: EventMetadata
    payload: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Kafka serialization"""
        return {
            "metadata": asdict(self.metadata),
            "payload": self.payload
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelfMonitorEvent':
        """Create event from dictionary"""
        metadata = EventMetadata(**data["metadata"])
        return cls(metadata=metadata, payload=data["payload"])

class KafkaEventProducer:
    """High-level Kafka producer for SelfMonitor events"""
    
    def __init__(self, 
                 service_name: str,
                 bootstrap_servers: str = "localhost:9092",
                 enable_idempotence: bool = True):
        self.service_name = service_name
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        
        if kafka_available:
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=bootstrap_servers,
                    value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                    key_serializer=lambda x: x.encode('utf-8') if x else None,
                    enable_idempotence=enable_idempotence,
                    acks='all',  # Wait for all replicas
                    retries=3,
                    batch_size=16384,  # Batch size for better throughput
                    linger_ms=10,      # Small batching delay
                    compression_type='snappy'
                )
                logger.info(f"✓ Kafka producer initialized for {service_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                self.producer = None
        else:
            logger.warning("kafka-python not available, events will not be sent to Kafka")
    
    async def send_event(self, 
                        topic: str, 
                        event_type: str,
                        payload: Dict[str, Any],
                        key: Optional[str] = None,
                        user_id: Optional[str] = None,
                        correlation_id: Optional[str] = None) -> bool:
        """Send event to Kafka topic"""
        
        if not self.producer:
            logger.warning(f"Kafka producer not available, dropping event: {event_type}")
            return False
        
        try:
            # Create event metadata
            metadata = EventMetadata(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                service_name=self.service_name,
                event_type=event_type,
                correlation_id=correlation_id,
                user_id=user_id
            )
            
            # Create structured event
            event = SelfMonitorEvent(metadata=metadata, payload=payload)
            
            # Send to Kafka
            future = self.producer.send(
                topic=topic,
                value=event.to_dict(),
                key=key or user_id
            )
            
            # Wait for send confirmation
            record_metadata = future.get(timeout=10)
            
            logger.debug(f"Event sent: {event_type} → {topic} (partition {record_metadata.partition})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send event {event_type} to {topic}: {e}")
            return False
    
    async def send_user_event(self, event_type: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Send user lifecycle event"""
        return await self.send_event(
            topic="user.lifecycle",
            event_type=event_type, 
            payload=data,
            key=user_id,
            user_id=user_id
        )
    
    async def send_transaction_event(self, event_type: str, transaction_data: Dict[str, Any]) -> bool:
        """Send transaction event"""
        user_id = transaction_data.get("user_id")
        transaction_id = transaction_data.get("transaction_id")
        
        return await self.send_event(
            topic="transactions.stream",
            event_type=event_type,
            payload=transaction_data,
            key=transaction_id,
            user_id=user_id
        )
    
    async def send_ai_event(self, event_type: str, prediction_data: Dict[str, Any]) -> bool:
        """Send AI/ML prediction event"""
        user_id = prediction_data.get("user_id")
        
        return await self.send_event(
            topic="ai.predictions", 
            event_type=event_type,
            payload=prediction_data,
            key=user_id,
            user_id=user_id
        )
    
    async def send_fraud_event(self, event_type: str, fraud_data: Dict[str, Any]) -> bool:
        """Send fraud detection event"""
        user_id = fraud_data.get("user_id")
        
        return await self.send_event(
            topic="fraud.alerts",
            event_type=event_type,
            payload=fraud_data,
            key=user_id,
            user_id=user_id
        )
        
    def close(self):
        """Close producer and flush pending messages"""
        if self.producer:
            self.producer.flush()
            self.producer.close()

class KafkaEventConsumer:
    """High-level Kafka consumer for SelfMonitor events"""
    
    def __init__(self,
                 service_name: str,
                 group_id: str,
                 topics: List[str],
                 bootstrap_servers: str = "localhost:9092",
                 auto_offset_reset: str = "earliest"):
        self.service_name = service_name
        self.group_id = group_id
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        self.event_handlers: Dict[str, Callable] = {}
        
        if kafka_available:
            try:
                self.consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=bootstrap_servers,
                    group_id=group_id,
                    auto_offset_reset=auto_offset_reset,
                    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                    key_deserializer=lambda x: x.decode('utf-8') if x else None,
                    max_poll_records=500,
                    session_timeout_ms=30000,
                    heartbeat_interval_ms=10000
                )
                logger.info(f"✓ Kafka consumer initialized: {group_id} for {topics}")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka consumer: {e}")
                self.consumer = None
        else:
            logger.warning("kafka-python not available, consumer disabled")
    
    def register_handler(self, event_type: str, handler: Callable[[SelfMonitorEvent], None]):
        """Register event handler for specific event type"""
        self.event_handlers[event_type] = handler
        logger.info(f"Registered handler for {event_type}")
    
    async def start_consuming(self):
        """Start consuming events from Kafka"""
        if not self.consumer:
            logger.error("Kafka consumer not available")
            return
            
        logger.info(f"🚀 Starting event consumption for {self.group_id}")
        
        try:
            for message in self.consumer:
                try:
                    # Parse event
                    event_data = message.value
                    event = SelfMonitorEvent.from_dict(event_data)
                    
                    # Find and execute handler
                    event_type = event.metadata.event_type
                    if event_type in self.event_handlers:
                        handler = self.event_handlers[event_type]
                        await self._execute_handler(handler, event)
                    else:
                        logger.warning(f"No handler registered for event: {event_type}")
                        
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    # Could implement dead letter queue here
                    
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
    
    async def _execute_handler(self, handler: Callable, event: SelfMonitorEvent):
        """Execute event handler with error handling"""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
                
            logger.debug(f"Processed event: {event.metadata.event_type}")
            
        except Exception as e:
            logger.error(f"Handler error for {event.metadata.event_type}: {e}")
            # Could increment error metrics here

class EventStreamingMixin:
    """Mixin class for FastAPI services to add event streaming capabilities"""
    
    def __init__(self, service_name: str, **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name
        self.event_producer = KafkaEventProducer(service_name)
        
    async def emit_event(self, event_type: str, data: Dict[str, Any], **kwargs) -> bool:
        """Emit event from service"""
        return await self.event_producer.send_event(
            topic=self._get_topic_for_event(event_type),
            event_type=event_type,
            payload=data,
            **kwargs
        )
    
    def _get_topic_for_event(self, event_type: str) -> str:
        """Map event type to appropriate Kafka topic"""
        event_topic_mapping = {
            # User events
            "user.registered": "user.lifecycle",
            "user.updated": "user.lifecycle",
            "user.deleted": "user.lifecycle",
            
            # Transaction events  
            "transaction.created": "transactions.stream",
            "transaction.processed": "transactions.stream",
            "transaction.categorized": "transactions.stream",
            
            # AI events
            "prediction.generated": "ai.predictions",
            "recommendation.served": "ai.predictions",
            "model.retrained": "ai.predictions",
            
            # Fraud events
            "fraud.alert": "fraud.alerts",
            "fraud.investigation": "fraud.alerts",
            
            # Analytics events
            "metric.calculated": "analytics.metrics",
            "dashboard.viewed": "analytics.metrics",
            
            # System events
            "service.health": "system.monitoring",
            "error.occurred": "system.monitoring"
        }
        
        return event_topic_mapping.get(event_type, "system.monitoring")
    
    async def cleanup_producer(self):
        """Cleanup event producer"""
        if hasattr(self, 'event_producer'):
            self.event_producer.close()

# Factory functions for easy integration
def create_event_producer(service_name: str) -> KafkaEventProducer:
    """Factory function to create event producer"""
    return KafkaEventProducer(service_name)

def create_event_consumer(service_name: str, group_id: str, topics: List[str]) -> KafkaEventConsumer:
    """Factory function to create event consumer"""
    return KafkaEventConsumer(service_name, group_id, topics)

# Example usage patterns
async def example_usage():
    """Example of how to use the event streaming library"""
    
    # Producer example
    producer = create_event_producer("predictive-analytics")
    
    await producer.send_ai_event("prediction.generated", {
        "user_id": "user_123",
        "model_name": "churn_prediction",
        "confidence": 0.87,
        "prediction": "low_churn_risk"
    })
    
    # Consumer example
    consumer = create_event_consumer(
        service_name="fraud-detection",
        group_id="fraud-realtime",
        topics=["transactions.stream", "auth.events"]
    )
    
    # Register event handlers
    async def handle_transaction(event: SelfMonitorEvent):
        transaction_data = event.payload
        print(f"Processing transaction: {transaction_data}")
        
    consumer.register_handler("transaction.created", handle_transaction)
    
    # Start consuming (in background)
    # await consumer.start_consuming()

if __name__ == "__main__":
    print("SelfMonitor Kafka Integration Library")
    print("Use this library in microservices for event streaming")
    
    # Run example
    asyncio.run(example_usage())