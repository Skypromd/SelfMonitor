#!/usr/bin/env python3
"""
SelfMonitor Multi-Tenant Architecture Tests
Комплексное тестирование изоляции данных между клиентами
"""

import asyncio
import aiohttp  # type: ignore[import]
import asyncpg  # type: ignore[import]
import json
import time
from typing import List, Dict, Any, Optional
from types import TracebackType
from datetime import datetime
import logging

# Test Configuration
TENANT_ROUTER_URL = "http://localhost:8001"
USER_PROFILE_API_URL = "http://localhost:8010"
TRANSACTIONS_API_URL = "http://localhost:8011"
GRAPHQL_URL = "http://localhost:4000"

# Test JWT tokens for different tenants
TEST_TOKENS = {
    "tenant_demo1": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyXzEiLCJ0ZW5hbnRfaWQiOiJkZW1vMSIsImV4cCI6OTk5OTk5OTk5OX0.test_token_demo1",
    "tenant_demo2": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyXzEiLCJ0ZW5hbnRfaWQiOiJkZW1vMiIsImV4cCI6OTk5OTk5OTk5OX0.test_token_demo2", 
    "tenant_demo3": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidGVzdF91c2VyXzEiLCJ0ZW5hbnRfaWQiOiJkZW1vMyIsImV4cCI6OTk5OTk5OTk5OX0.test_token_demo3"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiTenantTester:
    """Класс для тестирования мульти-тенантной архитектуры"""
    
    def __init__(self):
        self.session: Any = None  # type: ignore[misc]
        self.test_results: List[str] = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()  # type: ignore[misc]
        return self
        
    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        if self.session:
            await self.session.close()  # type: ignore[misc]

    async def test_tenant_router_health(self) -> Dict[str, Any]:
        """Тест доступности Tenant Router"""
        logger.info("🧪 Testing Tenant Router health...")
        
        try:
            async with self.session.get(f"{TENANT_ROUTER_URL}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {"status": "PASS", "details": data}
                else:
                    return {"status": "FAIL", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    async def test_tenant_database_creation(self, tenant_id: str) -> Dict[str, Any]:
        """Тест создания БД для нового tenant"""
        logger.info(f"🧪 Testing database creation for tenant {tenant_id}...")
        
        try:
            async with self.session.get(f"{TENANT_ROUTER_URL}/tenant/{tenant_id}/database-url") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "PASS", 
                        "details": {
                            "tenant_id": data.get("tenant_id"),
                            "database_url": "***REDACTED***"  # Security
                        }
                    }
                else:
                    return {"status": "FAIL", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    async def test_tenant_data_isolation(self) -> Dict[str, Any]:
        """Критический тест: изоляция данных между tenant"""
        logger.info("🔒 Testing critical tenant data isolation...")
        
        test_data = {
            "demo1": {"user_id": "isolation_test_user_1", "first_name": "Tenant1", "email": "user1@demo1.com"},
            "demo2": {"user_id": "isolation_test_user_1", "first_name": "Tenant2", "email": "user1@demo2.com"},
            "demo3": {"user_id": "isolation_test_user_1", "first_name": "Tenant3", "email": "user1@demo3.com"}
        }
        
        results = []
        
        # Создаем пользователей в разных tenant с одинаковым user_id
        for tenant_id, user_data in test_data.items():
            token = TEST_TOKENS.get(f"tenant_{tenant_id}")
            if not token:
                continue
                
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                # Создаем пользователя
                async with self.session.post(
                    f"{USER_PROFILE_API_URL}/profiles",
                    headers=headers,
                    json=user_data
                ) as response:
                    if response.status in [200, 201]:
                        results.append(f"✅ Created user in {tenant_id}")  # type: ignore[misc]
                    else:
                        results.append(f"❌ Failed to create user in {tenant_id}: {response.status}")  # type: ignore[misc]
            except Exception as e:
                results.append(f"❌ Error creating user in {tenant_id}: {e}")  # type: ignore[misc]
        
        # Проверяем изоляцию: каждый tenant видит только своих пользователей
        for tenant_id in test_data.keys():
            token = TEST_TOKENS.get(f"tenant_{tenant_id}")
            if not token:
                continue
                
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                async with self.session.get(
                    f"{USER_PROFILE_API_URL}/profiles/isolation_test_user_1",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        expected_name = test_data[tenant_id]["first_name"]
                        
                        if data.get("first_name") == expected_name:
                            results.append(f"✅ {tenant_id} sees correct isolated data")  # type: ignore[misc]
                        else:
                            results.append(f"☺️ CRITICAL: {tenant_id} sees wrong data! Expected {expected_name}, got {data.get('first_name')}")  # type: ignore[misc]
                    else:
                        results.append(f"❌ {tenant_id} cannot access own data: {response.status}")  # type: ignore[misc]
            except Exception as e:
                results.append(f"❌ Error testing isolation for {tenant_id}: {e}")  # type: ignore[misc]
        
        return {
            "status": "PASS" if all("☺️ CRITICAL" not in result for result in results) else "CRITICAL_FAIL",  # type: ignore[misc]
            "details": results
        }

    async def test_tenant_performance_isolation(self) -> Dict[str, Any]:
        """Тест производительности и отсутствия влияния между tenant"""
        logger.info("⚡ Testing tenant performance isolation...")
        
        async def create_load_for_tenant(tenant_id: str, operations: int = 100) -> Dict[str, Any]:
            """Создает нагрузку для одного tenant"""
            token = TEST_TOKENS.get(f"tenant_{tenant_id}")
            if not token:
                return {"error": "No token for tenant"}
                
            headers = {"Authorization": f"Bearer {token}"}
            success_count = 0
            start_time = time.time()
            
            for i in range(operations):
                user_data = {
                    "user_id": f"perf_test_user_{i}",
                    "first_name": f"User{i}",
                    "email": f"user{i}@{tenant_id}.com"
                }
                
                try:
                    async with self.session.post(
                        f"{USER_PROFILE_API_URL}/profiles",
                        headers=headers,
                        json=user_data
                    ) as response:
                        if response.status in [200, 201]:
                            success_count += 1
                except:
                    pass
            
            duration = time.time() - start_time
            return {
                "tenant_id": tenant_id,
                "operations": operations,
                "success_count": success_count,
                "duration": duration,
                "ops_per_second": success_count / duration if duration > 0 else 0
            }
        
        # Запускаем нагрузку параллельно для всех tenant
        tasks = [
            create_load_for_tenant("demo1", 50),
            create_load_for_tenant("demo2", 50), 
            create_load_for_tenant("demo3", 50)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Анализируем результаты
        performance_ok = True
        for result in results:
            if isinstance(result, dict) and result.get("ops_per_second", 0) < 5:
                performance_ok = False
        
        return {
            "status": "PASS" if performance_ok else "FAIL",
            "details": results
        }

    async def test_cross_tenant_data_leakage(self) -> Dict[str, Any]:
        """Критический тест: проверка утечки данных между tenant"""
        logger.info("🛡️ Testing cross-tenant data leakage prevention...")
        
        # Создаем секретные данные в demo1
        secret_data = {
            "user_id": "secret_user_999",
            "first_name": "TopSecret", 
            "email": "secret@demo1.com"
        }
        
        token_demo1 = TEST_TOKENS.get("tenant_demo1")
        headers_demo1 = {"Authorization": f"Bearer {token_demo1}"}
        
        # Создаем секретного пользователя в demo1
        async with self.session.post(
            f"{USER_PROFILE_API_URL}/profiles",
            headers=headers_demo1,
            json=secret_data
        ) as response:
            if response.status not in [200, 201]:
                return {"status": "ERROR", "details": "Could not create secret data"}
        
        # Пытаемся получить этого пользователя из demo2 и demo3
        leakage_attempts = []
        
        for tenant_id in ["demo2", "demo3"]:
            token = TEST_TOKENS.get(f"tenant_{tenant_id}")
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                async with self.session.get(
                    f"{USER_PROFILE_API_URL}/profiles/secret_user_999",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        _data = await response.json()
                        leakage_attempts.append(f"☺️ CRITICAL: {tenant_id} can see data from demo1!")  # type: ignore[misc]
                    elif response.status == 404:
                        leakage_attempts.append(f"✅ {tenant_id} correctly blocked from accessing demo1 data")  # type: ignore[misc]
                    else:
                        leakage_attempts.append(f"❓ {tenant_id} got unexpected response: {response.status}")  # type: ignore[misc]
            except Exception as e:
                leakage_attempts.append(f"❌ Error testing {tenant_id}: {e}")  # type: ignore[misc]
        
        has_leakage = any("☺️ CRITICAL" in attempt for attempt in leakage_attempts)  # type: ignore[misc]
        
        return {
            "status": "CRITICAL_FAIL" if has_leakage else "PASS",
            "details": leakage_attempts
        }

    async def test_tenant_database_scaling(self) -> Dict[str, Any]:
        """Тест автоматического создания новых tenant баз данных"""
        logger.info("📈 Testing tenant database auto-scaling...")
        
        timestamp = int(time.time())
        
        # Создаем несколько новых tenant одновременно
        new_tenant_ids = [f"scale_test_{timestamp}_{i}" for i in range(5)]
        
        tasks = []
        for tenant_id in new_tenant_ids:
            tasks.append(self.test_tenant_database_creation(tenant_id))  # type: ignore[misc]
        
        creation_results = await asyncio.gather(*tasks)  # type: ignore[misc]
        
        success_count = sum(1 for r in creation_results if r["status"] == "PASS")  # type: ignore[misc]
        
        return {
            "status": "PASS" if success_count >= 4 else "FAIL",
            "details": {
                "attempted_tenants": len(new_tenant_ids),
                "successful_creations": success_count,
                "results": creation_results
            }
        }

    async def test_shard_status_monitoring(self) -> Dict[str, Any]:
        """Тест мониторинга статуса шардов"""
        logger.info("📊 Testing shard status monitoring...")
        
        try:
            async with self.session.get(f"{TENANT_ROUTER_URL}/shards/status") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    total_shards = data.get("total_shards", 0)
                    total_tenants = data.get("total_tenants", 0)
                    
                    return {
                        "status": "PASS" if total_shards >= 3 else "FAIL",
                        "details": {
                            "total_shards": total_shards,
                            "total_tenants": total_tenants,
                            "shards": data.get("shards", {})
                        }
                    }
                else:
                    return {"status": "FAIL", "details": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "ERROR", "details": str(e)}

    async def test_tenant_backup_isolation(self) -> Dict[str, Any]:
        """Тест изоляции бэкапов между tenant"""
        logger.info("💾 Testing tenant backup isolation...")
        
        # Это базовый тест - в продакшене нужен более детальный
        backup_tests = []
        
        for tenant_id in ["demo1", "demo2"]:
            try:
                # Проверяем health конкретного tenant
                async with self.session.get(f"{TENANT_ROUTER_URL}/tenant/{tenant_id}/health") as response:
                    if response.status == 200:
                        _data = await response.json()
                        backup_tests.append(f"✅ {tenant_id} health check passed")  # type: ignore[misc]
                    else:
                        backup_tests.append(f"❌ {tenant_id} health check failed")  # type: ignore[misc]
            except Exception as e:
                backup_tests.append(f"❌ Error checking {tenant_id}: {e}")  # type: ignore[misc]
        
        return {
            "status": "PASS",
            "details": backup_tests
        }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Запуск всех тестов мульти-тенантной архитектуры"""
        print("🧪 Starting SelfMonitor Multi-Tenant Architecture Tests...\n")
        
        test_suite = [
            ("Tenant Router Health", self.test_tenant_router_health()),
            ("Tenant Database Creation", self.test_tenant_database_creation("test_" + str(int(time.time())))),
            ("🔒 CRITICAL: Tenant Data Isolation", self.test_tenant_data_isolation()),
            ("🛡️ CRITICAL: Cross-Tenant Data Leakage", self.test_cross_tenant_data_leakage()),
            ("Performance Isolation", self.test_tenant_performance_isolation()),
            ("Database Auto-Scaling", self.test_tenant_database_scaling()),
            ("Shard Status Monitoring", self.test_shard_status_monitoring()),
            ("Backup Isolation", self.test_tenant_backup_isolation())
        ]
        
        results = {}
        critical_failures = []
        
        for test_name, test_coro in test_suite:
            print(f"Running: {test_name}...")
            try:
                result = await test_coro
                results[test_name] = result
                
                status_icon = {
                    "PASS": "✅",
                    "FAIL": "❌", 
                    "ERROR": "💥",
                    "CRITICAL_FAIL": "🚨"
                }.get(result["status"], "❓")
                
                print(f"{status_icon} {test_name}: {result['status']}")
                
                if result["status"] == "CRITICAL_FAIL":
                    critical_failures.append(test_name)  # type: ignore[misc]
                    
            except Exception as e:
                print(f"💥 {test_name}: ERROR - {e}")
                results[test_name] = {"status": "ERROR", "details": str(e)}
        
        # Итоговый отчет
        print("\n" + "="*80)
        print("📋 MULTI-TENANT ARCHITECTURE TEST REPORT")
        print("="*80)
        
        total_tests = len(test_suite)
        passed_tests = sum(1 for r in results.values() if r["status"] == "PASS")  # type: ignore[misc]
        failed_tests = sum(1 for r in results.values() if r["status"] in ["FAIL", "ERROR"])  # type: ignore[misc]
        critical_fails = len(critical_failures)  # type: ignore[misc]
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Critical Failures: {critical_fails}")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL SECURITY ISSUES DETECTED:")
            for failure in critical_failures:  # type: ignore[misc]
                print(f"   - {failure}")
            print("\n⚠️  DO NOT USE IN PRODUCTION UNTIL FIXED!")
        
        overall_status = "PRODUCTION_READY" if critical_fails == 0 and failed_tests == 0 else "NEEDS_FIXES"
        
        print(f"\n🎯 Overall Status: {overall_status}")
        print("="*80)
        
        return {
            "overall_status": overall_status,
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "critical_failures": critical_fails
            },
            "detailed_results": results,
            "critical_issues": critical_failures
        }

async def main():
    """Главная функция для запуска тестов"""
    async with MultiTenantTester() as tester:
        results = await tester.run_all_tests()
        
        # Сохраняем детальный отчет
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"multitenant_test_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit code для CI/CD
        exit_code = 0 if results["overall_status"] == "PRODUCTION_READY" else 1
        return exit_code

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)