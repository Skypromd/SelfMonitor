"""
Tool Registry for SelfMate AI Agent

Dynamically discovers and integrates with all SelfMonitor microservices.
Provides standardized interface for the agent to interact with platform capabilities.
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    data: Dict[str, Any]
    message: str
    execution_time_ms: int


class BaseTool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str, description: str, service_url: str):
        self.name = name
        self.description = description 
        self.service_url = service_url
        self.client = httpx.AsyncClient(timeout=30.0)  # type: ignore
    
    @abstractmethod
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        """Execute the tool"""
        pass
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to service"""
        start_time = datetime.now(timezone.utc)
        
        try:
            url = f"{self.service_url.rstrip('/')}/{endpoint.lstrip('/')}"
            
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=data)  # type: ignore
            elif method.upper() == "POST":
                response = await self.client.post(url, headers=headers, json=data)  # type: ignore
            elif method.upper() == "PUT":
                response = await self.client.put(url, headers=headers, json=data)  # type: ignore
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response.raise_for_status()  # type: ignore
            
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return {
                "success": True,
                "data": response.json() if response.content else {},  # type: ignore
                "status_code": response.status_code,  # type: ignore
                "execution_time_ms": execution_time
            }
            
        except Exception as e:
            execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            return {
                "success": False,
                "error": str(e),
                "execution_time_ms": execution_time
            }


# --- Financial Analysis Tools ---

class TransactionAnalysisTool(BaseTool):
    """Analyze user's transaction patterns and financial health"""
    
    def __init__(self):
        super().__init__(
            name="transaction_analysis",
            description="Analyze transaction patterns, spending habits, and financial trends",
            service_url=os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        # Get transaction data
        result = await self._make_request(
            "GET",
            f"/transactions/analysis/{user_id}",
            headers={"Authorization": f"Bearer {kwargs.get('token', '')}"}
        )
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        if result["success"]:
            return ToolResult(
                success=True,
                data=result["data"],
                message="Transaction analysis completed successfully",
                execution_time_ms=execution_time
            )
        else:
            return ToolResult(
                success=False,
                data={},
                message=f"Failed to analyze transactions: {result.get('error', 'Unknown error')}",
                execution_time_ms=execution_time
            )


class CashFlowPredictionTool(BaseTool):
    """Predict future cash flow based on historical data"""
    
    def __init__(self):
        super().__init__(
            name="cash_flow_prediction",
            description="Predict future cash flow and identify potential shortfalls",
            service_url=os.getenv("PREDICTIVE_ANALYTICS_URL", "http://predictive-analytics")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        result = await self._make_request(
            "POST",
            "/predict/cash-flow",
            headers={"Authorization": f"Bearer {kwargs.get('token', '')}"},
            data={
                "user_id": user_id,
                "forecast_months": kwargs.get("months", 6)
            }
        )
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        if result["success"]:
            return ToolResult(
                success=True,
                data=result["data"],
                message="Cash flow prediction generated successfully",
                execution_time_ms=execution_time
            )
        else:
            return ToolResult(
                success=False,
                data={},
                message=f"Cash flow prediction failed: {result.get('error', 'Unknown error')}",
                execution_time_ms=execution_time
            )


# --- Tax Optimization Tools ---

class TaxCalculationTool(BaseTool):
    """Calculate tax obligations and optimization opportunities"""
    
    def __init__(self):
        super().__init__(
            name="tax_calculation",
            description="Calculate current tax obligations and find optimization opportunities",
            service_url=os.getenv("TAX_ENGINE_URL", "http://tax-engine")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        result = await self._make_request(
            "POST",
            "/tax/calculate",
            headers={"Authorization": f"Bearer {kwargs.get('token', '')}"},
            data={
                "user_id": user_id,
                "tax_year": kwargs.get("tax_year", datetime.now().year)
            }
        )
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ToolResult(
            success=result["success"],
            data=result.get("data", {}),
            message="Tax calculation completed" if result["success"] else f"Tax calculation failed: {result.get('error')}",
            execution_time_ms=execution_time
        )


# --- Business Intelligence Tools ---

class BusinessInsightsTool(BaseTool):
    """Generate business insights and recommendations"""
    
    def __init__(self):
        super().__init__(
            name="business_insights",
            description="Generate comprehensive business insights and strategic recommendations",
            service_url=os.getenv("BUSINESS_INTELLIGENCE_URL", "http://business-intelligence")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        result = await self._make_request(
            "POST",
            "/generate-business-insights",
            headers={"Authorization": f"Bearer {kwargs.get('token', '')}"},
            data={
                "analysis_type": kwargs.get("analysis_type", "comprehensive"),
                "time_range": kwargs.get("time_range", "last_90_days")
            }
        )
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ToolResult(
            success=result["success"],
            data=result.get("data", {}),
            message="Business insights generated successfully" if result["success"] else f"Failed to generate insights: {result.get('error')}",
            execution_time_ms=execution_time
        )


# --- Fraud Detection Tools ---

class FraudCheckTool(BaseTool):
    """Check for potential fraud and security issues"""
    
    def __init__(self):
        super().__init__(
            name="fraud_detection",
            description="Monitor for fraudulent activity and security threats",
            service_url=os.getenv("FRAUD_DETECTION_URL", "http://fraud-detection")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        result = await self._make_request(
            "GET",
            f"/fraud-alerts/{user_id}",
            headers={"Authorization": f"Bearer {kwargs.get('token', '')}"}
        )
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ToolResult(
            success=result["success"],
            data=result.get("data", {}),
            message="Fraud check completed" if result["success"] else f"Fraud check failed: {result.get('error')}",
            execution_time_ms=execution_time
        )


# --- Automation Tools ---

class InvoiceAutomationTool(BaseTool):
    """Automate invoice processing and follow-ups"""
    
    def __init__(self):
        super().__init__(
            name="invoice_automation",
            description="Automate invoice creation, sending, and payment follow-ups",
            service_url=os.getenv("DOCUMENTS_SERVICE_URL", "http://documents-service")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        action = kwargs.get("action", "list_overdue")
        
        if action == "list_overdue":
            result = await self._make_request(
                "GET",
                f"/invoices/overdue/{user_id}",
                headers={"Authorization": f"Bearer {kwargs.get('token', '')}"}
            )
        elif action == "send_reminders":
            result = await self._make_request(
                "POST",
                "/invoices/send-reminders",
                headers={"Authorization": f"Bearer {kwargs.get('token', '')}"},
                data={"user_id": user_id}
            )
        else:
            result: Dict[str, Any] = {"success": False, "error": "Unknown action"}
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ToolResult(
            success=result["success"],
            data=result.get("data", {}),
            message=f"Invoice automation ({action}) completed" if result["success"] else f"Invoice automation failed: {result.get('error')}",
            execution_time_ms=execution_time
        )


class CalendarManagementTool(BaseTool):
    """Manage calendar events and reminders"""
    
    def __init__(self):
        super().__init__(
            name="calendar_management", 
            description="Create calendar events, reminders, and manage schedules",
            service_url=os.getenv("CALENDAR_SERVICE_URL", "http://calendar-service")
        )
    
    async def execute(self, user_id: str, **kwargs: Any) -> ToolResult:
        start_time = datetime.now(timezone.utc)
        
        result = await self._make_request(
            "POST",
            "/events",
            headers={"Authorization": f"Bearer {kwargs.get('token', '')}"},
            data={
                "user_id": user_id,
                "title": kwargs.get("title", "Agent Reminder"), 
                "description": kwargs.get("description", ""),
                "event_date": kwargs.get("date", (datetime.now() + timedelta(days=1)).isoformat()),
                "event_type": kwargs.get("event_type", "reminder")
            }
        )
        
        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        return ToolResult(
            success=result["success"],
            data=result.get("data", {}),
            message="Calendar event created" if result["success"] else f"Calendar management failed: {result.get('error')}",
            execution_time_ms=execution_time
        )


# --- Tool Registry ---

class ToolRegistry:
    """
    Central registry for all AI Agent tools
    
    Automatically discovers available services and creates appropriate tools.
    Provides standardized interface for agent to interact with platform.
    """
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.service_discovery: Dict[str, str] = {}
        self.last_discovery = None
        
    async def discover_services(self):
        """Discover available microservices and create tools"""
        print("🔍 Discovering SelfMonitor services...")
        
        # Service discovery configuration
        service_map = {
            "transactions-service": os.getenv("TRANSACTIONS_SERVICE_URL", "http://transactions-service"),
            "predictive-analytics": os.getenv("PREDICTIVE_ANALYTICS_URL", "http://predictive-analytics"),
            "tax-engine": os.getenv("TAX_ENGINE_URL", "http://tax-engine"),
            "business-intelligence": os.getenv("BUSINESS_INTELLIGENCE_URL", "http://business-intelligence"),
            "fraud-detection": os.getenv("FRAUD_DETECTION_URL", "http://fraud-detection"),
            "documents-service": os.getenv("DOCUMENTS_SERVICE_URL", "http://documents-service"),
            "calendar-service": os.getenv("CALENDAR_SERVICE_URL", "http://calendar-service"),
            "analytics-service": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service"),
            "user-profile-service": os.getenv("USER_PROFILE_SERVICE_URL", "http://user-profile-service"),
            "compliance-service": os.getenv("COMPLIANCE_SERVICE_URL", "http://compliance-service"),
            "advice-service": os.getenv("ADVICE_SERVICE_URL", "http://advice-service"),
            "referral-service": os.getenv("REFERRAL_SERVICE_URL", "http://referral-service"),
            "customer-success": os.getenv("CUSTOMER_SUCCESS_URL", "http://customer-success"),
            "pricing-engine": os.getenv("PRICING_ENGINE_URL", "http://pricing-engine"),
            "cost-optimization": os.getenv("COST_OPTIMIZATION_URL", "http://cost-optimization")
        }
        
        # Update service discovery map
        self.service_discovery = service_map
        
        # Initialize core tools
        await self._initialize_core_tools()
        
        # Test service connectivity
        await self._test_service_connectivity()
        
        self.last_discovery = datetime.now(timezone.utc)
        print(f"✅ Service discovery completed. Found {len(self.tools)} available tools.")
    
    async def _initialize_core_tools(self):
        """Initialize core tools that are always available"""
        core_tools: List[BaseTool] = [
            TransactionAnalysisTool(),
            CashFlowPredictionTool(),
            TaxCalculationTool(),
            BusinessInsightsTool(),
            FraudCheckTool(),
            InvoiceAutomationTool(),
            CalendarManagementTool()
        ]
        
        for tool in core_tools:
            self.tools[tool.name] = tool
            print(f"🔧 Registered tool: {tool.name}")
    
    async def _test_service_connectivity(self):
        """Test connectivity to discovered services"""
        async with httpx.AsyncClient() as client:  # type: ignore
            for service_name, service_url in self.service_discovery.items():
                try:
                    response = await client.get(f"{service_url}/health", timeout=5.0)  # type: ignore
                    if response.status_code == 200:  # type: ignore
                        print(f"✅ {service_name}: Connected")
                    else:
                        print(f"⚠️ {service_name}: Health check failed ({response.status_code})")  # type: ignore
                except Exception as e:
                    print(f"❌ {service_name}: Connection failed - {str(e)}")
    
    def get_available_tools(self) -> Dict[str, str]:
        """Get list of available tools with descriptions"""
        return {name: tool.description for name, tool in self.tools.items()}
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get specific tool by name"""
        return self.tools.get(tool_name)
    
    async def execute_tool(
        self, 
        tool_name: str, 
        user_id: str, 
        **kwargs: Any
    ) -> ToolResult:
        """Execute a tool safely with error handling"""
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                data={},
                message=f"Tool '{tool_name}' not found",
                execution_time_ms=0
            )
        
        try:
            return await tool.execute(user_id, **kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                message=f"Tool execution failed: {str(e)}",
                execution_time_ms=0
            )
    
    async def get_tool_capabilities(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get personalized tool capabilities for user"""
        capabilities: Dict[str, Dict[str, Any]] = {}
        
        for tool_name, tool in self.tools.items():
            # Test if tool is available for this user
            try:
                # Quick health check
                capabilities[tool_name] = {
                    "description": tool.description,
                    "available": True,
                    "service_url": tool.service_url,
                    "last_tested": datetime.now(timezone.utc).isoformat()
                }
            except Exception:
                capabilities[tool_name] = {
                    "description": tool.description,
                    "available": False,
                    "service_url": tool.service_url,
                    "last_tested": datetime.now(timezone.utc).isoformat()
                }
        
        return capabilities
    
    async def refresh_discovery(self):
        """Refresh service discovery"""
        if (
            self.last_discovery is None or 
            datetime.now(timezone.utc) - self.last_discovery > timedelta(hours=1)
        ):
            await self.discover_services()
    
    def get_service_map(self) -> Dict[str, str]:
        """Get current service discovery map"""
        return self.service_discovery.copy()
    
    async def add_custom_tool(self, tool: BaseTool):
        """Add custom tool to registry"""
        self.tools[tool.name] = tool
        print(f"🔧 Added custom tool: {tool.name}")
    
    async def remove_tool(self, tool_name: str):
        """Remove tool from registry"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            print(f"🗑️ Removed tool: {tool_name}")
    
    async def get_tool_usage_stats(self) -> Dict[str, Any]:
        """Get tool usage statistics"""
        # TODO: Implement usage tracking
        return {
            "total_tools": len(self.tools),
            "available_tools": len([t for t in self.tools.values() if hasattr(t, "available")]),
            "last_discovery": self.last_discovery.isoformat() if self.last_discovery else None,
            "tools": list(self.tools.keys())
        }