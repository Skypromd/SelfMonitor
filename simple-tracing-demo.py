#!/usr/bin/env python3
"""
Simplified OpenTelemetry Tracing Demo for SelfMonitor
"""

import asyncio
import time
from typing import Dict, Any

print("="*60)
print("    SelfMonitor OpenTelemetry Integration Demo")
print("="*60)

# Check if telemetry components are available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    print("✓ OpenTelemetry SDK imported successfully")
    telemetry_available = True
except ImportError as e:
    print(f"✗ OpenTelemetry SDK not available: {e}")
    telemetry_available = False

if telemetry_available:
    # Setup basic tracing
    resource = Resource.create({
        SERVICE_NAME: "predictive-analytics-demo",
        SERVICE_VERSION: "2.0.0"
    })
    
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
    
    print("✓ OpenTelemetry tracer configured")
    
    # Demo async function with tracing
    async def demo_recommendation_generation(user_id: str) -> Dict[str, Any]:
        """Demo function showing distributed tracing in action"""
        with tracer.start_as_current_span("generate_recommendations") as span:
            span.set_attribute("user_id", user_id)
            span.set_attribute("operation", "ml_prediction")
            
            # Simulate data fetching
            with tracer.start_as_current_span("fetch_user_data") as child_span:
                child_span.set_attribute("service", "user-profile")
                await asyncio.sleep(0.1)  # Simulate network call
                user_data = {"user_id": user_id, "account_type": "premium"}
                child_span.set_attribute("data_size", len(user_data))
            
            # Simulate ML computation
            with tracer.start_as_current_span("ml_inference") as ml_span:
                ml_span.set_attribute("model", "recommendation_engine")
                await asyncio.sleep(0.05)  # Simulate computation
                recommendations = [
                    {"id": "rec_1", "priority": "high", "confidence": 0.92},
                    {"id": "rec_2", "priority": "medium", "confidence": 0.87}
                ]
                ml_span.set_attribute("recommendations_count", len(recommendations))
            
            result = {
                "user_data": user_data,
                "recommendations": recommendations,
                "processing_time_ms": 150
            }
            
            span.set_attribute("result_size", len(result["recommendations"]))
            return result

    async def run_demo():
        """Run the tracing demonstration"""
        print("\n→ Running tracing demonstration...")
        
        # Test with multiple users concurrently
        test_users = ["user_123", "user_456", "user_789"]
        start_time = time.time()
        
        tasks = [demo_recommendation_generation(user_id) for user_id in test_users]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        print(f"✓ Generated {len(results)} recommendation sets")
        print(f"→ Total execution time: {(end_time - start_time)*1000:.0f}ms")
        print(f"→ Created spans for: data fetching, ML inference, recommendations")
        
        # Show example result
        print(f"\nExample result for {test_users[0]}:")
        print(f"  - Recommendations: {len(results[0]['recommendations'])}")
        print(f"  - Account type: {results[0]['user_data']['account_type']}")
        
        return results

    # Run the demo
    try:
        results = asyncio.run(run_demo())
        print(f"\n✓ OpenTelemetry integration working successfully!")
        print(f"→ {len(results)} operations traced")
        
        print(f"\nNext steps to see traces:")
        print(f"1. Start Jaeger: docker run -d -p 16686:16686 -p 14268:14268 jaegertracing/all-in-one")
        print(f"2. Add Jaeger exporter to send traces")
        print(f"3. View traces at: http://localhost:16686")
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()

else:
    print("\n✗ OpenTelemetry SDK not available")
    print("Install with: pip install opentelemetry-api opentelemetry-sdk")

print("\n" + "="*60)
print("              Tracing Integration Complete")
print("="*60)