#!/usr/bin/env python3
"""
OpenTelemetry Tracing Test for SelfMonitor
Test distributed tracing integration without full Docker stack
"""

import sys
import os
import asyncio
from typing import Dict, Any

# Add libs path for telemetry import
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__ if '__file__' in globals() else 'test-tracing.py')), 'libs'))

try:
    from observability.telemetry import TelemetryConfig, get_tracer, trace_async_function, add_span_attributes
    print("✓ OpenTelemetry imports successful")
    telemetry_available = True
except ImportError as e:
    print(f"✗ OpenTelemetry import failed: {e}")
    print("Install dependencies: pip install -r libs/observability/opentelemetry-requirements.txt")
    telemetry_available = False
    
    # Create dummy functions for graceful degradation
    def trace_async_function(name):
        def decorator(func):
            return func
        return decorator
    
    def add_span_attributes(**kwargs):
        pass
    
    TelemetryConfig = None
    get_tracer = None

class TracingTestService:
    """Mock service to test distributed tracing"""
    
    def __init__(self):
        if telemetry_available:
            self.telemetry = TelemetryConfig(
                service_name="tracing-test",
                service_version="1.0.0"
            )
            self.telemetry.setup_tracing()
            self.telemetry.instrument_libraries()
            self.tracer = get_tracer(__name__)
        else:
            self.tracer = None
    
    @trace_async_function("fetch_user_data")
    async def fetch_user_data(self, user_id: str) -> Dict[str, Any]:
        """Mock user data fetch with tracing"""
        if telemetry_available:
            add_span_attributes(
                user_id=user_id,
                operation="data_fetch",
                service="user-service"
            )
        
        # Simulate network delay
        await asyncio.sleep(0.1)
        
        return {
            "user_id": user_id,
            "name": f"Test User {user_id}",
            "account_type": "premium"
        }
    
    @trace_async_function("generate_recommendations")  
    async def generate_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Mock recommendations with tracing"""
        if telemetry_available:
            add_span_attributes(
                user_id=user_id,
                operation="ml_inference",
                model="recommendation_engine"
            )
        
        # Fetch user data (creates child span)
        user_data = await self.fetch_user_data(user_id)
        
        # Simulate ML computation
        await asyncio.sleep(0.05)
        
        recommendations = [
            {
                "id": "rec_1",
                "title": "Tax optimization tip",
                "priority": "high",
                "confidence": 0.92
            },
            {
                "id": "rec_2", 
                "title": "Investment suggestion",
                "priority": "medium",
                "confidence": 0.87
            }
        ]
        
        if telemetry_available:
            add_span_attributes(
                recommendations_count=len(recommendations),
                avg_confidence=sum(r["confidence"] for r in recommendations) / len(recommendations)
            )
        
        return {
            "user_data": user_data,
            "recommendations": recommendations,
            "timestamp": "2026-02-23T20:55:00Z"
        }

async def run_tracing_test():
    """Run comprehensive tracing test"""
    print("→ Starting OpenTelemetry tracing test...")
    
    test_service = TracingTestService()
    
    # Test multiple operations to generate spans
    test_users = ["user_123", "user_456", "user_789"]
    
    tasks = []
    for user_id in test_users:
        task = test_service.generate_recommendations(user_id)
        tasks.append(task)
    
    # Execute concurrent operations
    results = await asyncio.gather(*tasks)
    
    print(f"✓ Generated {len(results)} recommendation sets with tracing")
    
    if telemetry_available:
        print("→ Traces should be visible in Jaeger UI at: http://localhost:16686")
        print("→ Look for service: 'tracing-test'")
        print("→ Spans should show: fetch_user_data -> generate_recommendations")
    
    return results

def main():
    """Main test function"""
    print("=" * 60)
    print("SelfMonitor OpenTelemetry Tracing Test")
    print("=" * 60)
    
    if not telemetry_available:
        print("\n✗ OpenTelemetry not available")
        print("Install with: pip install -r libs/observability/opentelemetry-requirements.txt")
        return
    
    try:
        # Set mock Jaeger endpoint for testing
        os.environ["JAEGER_ENDPOINT"] = "http://localhost:14268/api/traces"
        os.environ["ENABLE_TRACING"] = "true"
        os.environ["TRACE_SAMPLE_RATE"] = "1.0"  # 100% sampling for testing
        
        # Run async test
        results = asyncio.run(run_tracing_test())
        
        print(f"\n✓ Test completed successfully!")
        print(f"→ Processed {len(results)} operations")
        print("\nNext steps:")
        print("1. Start Jaeger: docker run -d --name jaeger -p 16686:16686 -p 14268:14268 jaegertracing/all-in-one:latest")
        print("2. Re-run this test to see traces")
        print("3. View traces: http://localhost:16686")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()