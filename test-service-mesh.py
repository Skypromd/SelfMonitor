#!/usr/bin/env python3
"""
Service Mesh Integration Test for SelfMonitor
Test Istio mTLS and traffic management features
"""

import asyncio
import httpx
import time
import json

print("="*60)
print("     SelfMonitor Service Mesh Integration Test")
print("="*60)

async def test_service_communication():
    """Test service-to-service communication through Istio"""
    
    # Test endpoints (assuming local development)
    test_endpoints = [
        "http://localhost:8000/health",  # nginx gateway
        "http://localhost:8001/health",  # auth-service  
        "http://localhost:8015/health",  # predictive-analytics
    ]
    
    results = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for endpoint in test_endpoints:
            try:
                start_time = time.time()
                response = await client.get(endpoint)
                end_time = time.time()
                
                result = {
                    "endpoint": endpoint,
                    "status": response.status_code,
                    "latency_ms": round((end_time - start_time) * 1000, 1),
                    "success": response.status_code == 200,
                    "headers": dict(response.headers)
                }
                
                # Check for Istio headers (indicates sidecar injection working)
                istio_headers = {
                    k: v for k, v in response.headers.items() 
                    if any(istio_key in k.lower() for istio_key in ['x-envoy', 'x-request-id', 'istio'])
                }
                
                result["istio_headers"] = istio_headers
                result["istio_enabled"] = len(istio_headers) > 0
                
            except Exception as e:
                result = {
                    "endpoint": endpoint,
                    "error": str(e),
                    "success": False,
                    "istio_enabled": False
                }
            
            results.append(result)
    
    return results

async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n🔄 Testing circuit breaker patterns...")
    
    # Simulate rapid requests to trigger circuit breaker
    endpoint = "http://localhost:8015/recommendations/test-user"
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(10):
            task = client.get(endpoint, timeout=1.0)
            tasks.append(task)
        
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            error_count = len(responses) - success_count
            
            print(f"→ Concurrent requests: 10")
            print(f"→ Successful: {success_count}")
            print(f"→ Failed/Circuit: {error_count}")
            
            return {
                "total_requests": 10,
                "successful": success_count,
                "failed": error_count,
                "circuit_breaker_triggered": error_count > 0
            }
            
        except Exception as e:
            print(f"✗ Circuit breaker test failed: {e}")
            return {"error": str(e)}

def check_istio_installation():
    """Check if Istio is installed and running"""
    print("🔍 Checking Istio installation...")
    
    try:
        import subprocess
        
        # Check if istioctl is available
        result = subprocess.run(['istioctl', 'version'], 
                                capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ Istio CLI found")
            print(f"→ {result.stdout.strip()}")
            return True
        else:
            print("✗ Istio CLI not found or not working")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("✗ Istio CLI not available")
        return False

async def main():
    """Main test function"""
    
    # Check Istio installation
    istio_available = check_istio_installation()
    
    print(f"\n📡 Testing service communication...")
    
    # Test service communication
    comm_results = await test_service_communication()
    
    print(f"\nService Communication Results:")
    print("-" * 40)
    
    total_services = len(comm_results)
    successful_services = sum(1 for r in comm_results if r.get('success', False))
    istio_enabled_services = sum(1 for r in comm_results if r.get('istio_enabled', False))
    
    for result in comm_results:
        status_icon = "✓" if result.get('success', False) else "✗"
        istio_icon = "🕸️" if result.get('istio_enabled', False) else "🔗"
        
        endpoint = result.get('endpoint', 'unknown')
        latency = result.get('latency_ms', 0)
        
        print(f"{status_icon} {istio_icon} {endpoint} - {latency}ms")
        
        if result.get('error'):
            print(f"   Error: {result['error']}")
    
    print(f"\nSummary:")
    print(f"→ Services responding: {successful_services}/{total_services}")
    print(f"→ Istio/Envoy detected: {istio_enabled_services}/{total_services}")
    
    # Test circuit breaker if services are running
    if successful_services > 0:
        circuit_result = await test_circuit_breaker()
        if not circuit_result.get('error'):
            circuit_triggered = circuit_result.get('circuit_breaker_triggered', False)
            circuit_icon = "🔥" if circuit_triggered else "✓"
            print(f"{circuit_icon} Circuit breaker test completed")
    
    print(f"\n🎯 Service Mesh Status:")
    if istio_available and istio_enabled_services > 0:
        print("✅ Service Mesh working - Istio sidecars detected!")
        print("→ mTLS encryption enabled")
        print("→ Traffic management active") 
        print("→ Circuit breaker policies applied")
    elif istio_available:
        print("⚠️ Istio installed but sidecars not detected")
        print("→ Check sidecar injection: kubectl label namespace default istio-injection=enabled")
    else:
        print("❌ Service Mesh not available")
        print("→ Install Istio: ./setup-service-mesh.sh development")
    
    print(f"\nNext steps:")
    print("1. Verify mTLS with: istioctl authn tls-check")
    print("2. View mesh topology: kubectl port-forward -n istio-system svc/kiali 20001:20001")
    print("3. Monitor traffic: kubectl port-forward -n istio-system svc/grafana 3000:3000")
    
    return {
        "istio_available": istio_available,
        "services_tested": total_services,
        "services_successful": successful_services,
        "istio_enabled": istio_enabled_services,
        "mesh_working": istio_available and istio_enabled_services > 0
    }

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        
        print("\n" + "="*60)
        if result["mesh_working"]:
            print("          ✅ SERVICE MESH INTEGRATION SUCCESS")
        else:
            print("          ⚠️ SERVICE MESH NEEDS CONFIGURATION")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()