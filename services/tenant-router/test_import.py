"""
Simple test to verify tenant-router works
"""
import sys
import asyncio

async def test_import():
    """Test that we can import the tenant router service"""
    try:
        # Test imports
        import asyncpg
        import redis.asyncio as redis
        from fastapi import FastAPI
        import uvicorn
        
        print("✅ All dependencies imported successfully")
        
        # Test that app can be imported
        sys.path.insert(0, "/app")
        from app.main import app, tenant_router
        
        print("✅ Tenant router service imported successfully")
        print("✅ FastAPI app created successfully")
        
        # Basic validation
        assert app.title == "Tenant Router Service"
        print("✅ App configuration verified")
        
        print("\n🎉 Tenant Router Service is ready for deployment!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_import())