# GraphQL Federation Gateway

Apollo Federation Gateway that provides a unified GraphQL API for all SelfMonitor microservices. This gateway orchestrates 29+ microservices into a single, cohesive GraphQL endpoint with federated schema composition.

## 🚀 Architecture Overview

The GraphQL Gateway implements Apollo Federation 2.0 to create a supergraph that federates schemas from:

### Core Services (10)
- **auth-service** - Authentication, authorization, user management
- **user-profile-service** - User profiles, preferences, settings  
- **transactions-service** - Transaction management, categorization
- **analytics-service** - Financial analytics, reporting
- **advice-service** - Financial advice and recommendations
- **categorization-service** - Transaction categorization and ML models
- **banking-connector** - Open Banking and bank integrations
- **compliance-service** - Regulatory compliance, AML/KYC
- **documents-service** - Document management and OCR
- **calendar-service** - Calendar events and financial planning

### AI & ML Services (3)
- **ai-agent-service** - SelfMate AI assistant and automation
- **recommendation-engine** - Personalized recommendations
- **fraud-detection-service** - Real-time fraud detection

### Business Services (6)
- **business-intelligence** - Business analytics and reporting
- **customer-success-platform** - Customer engagement and success
- **pricing-engine** - Dynamic pricing and subscription management
- **payment-gateway** - Payment processing and subscriptions
- **tax-engine** - Tax calculations and reporting
- **partner-registry** - Partner integrations and marketplace

### Platform Services (10+)
- **integrations-service** - Third-party integrations
- **localization-service** - Multi-language support
- **consent-service** - GDPR consent management
- **qna-service** - Q&A knowledge base
- **notification-service** - Multi-channel notifications
- **audit-service** - Audit logs and compliance tracking
- **data-pipeline** - ETL and data processing
- **real-time-engine** - Real-time data streaming
- **backup-service** - Data backup and recovery
- **monitoring-service** - System monitoring and alerting

## 🔧 Features

### Federation Capabilities
- **Schema Composition** - Automatic schema federation and composition
- **Entity Resolution** - Cross-service entity resolution using `@key` directives
- **Type Extensions** - Seamless type extension across services
- **Distributed Queries** - Efficient query planning and execution

### Security & Authentication  
- **JWT Authentication** - Token-based authentication with automatic forwarding
- **Role-Based Access** - Fine-grained authorization with role checking
- **Multi-tenant Support** - Tenant isolation and data access control
- **Rate Limiting** - Built-in rate limiting and DDoS protection

### Observability
- **OpenTelemetry Tracing** - Distributed tracing across all services
- **Performance Monitoring** - Query performance and latency tracking
- **Error Tracking** - Centralized error logging and monitoring
- **Health Checks** - Service health monitoring and reporting

### Developer Experience
- **GraphQL Playground** - Interactive query exploration (development)
- **Schema Introspection** - Full schema documentation and exploration
- **Query Validation** - Real-time query validation and error reporting
- **Type-Safe Operations** - Generated TypeScript types for frontend

## 📊 Performance & Scaling

### Query Optimization
- **Query Planning** - Intelligent query planning and execution
- **DataLoader Pattern** - Automatic N+1 query resolution
- **Caching Strategy** - Multi-level caching (Redis, in-memory)
- **Batch Operations** - Request batching and deduplication

### Horizontal Scaling
- **Stateless Design** - Fully stateless for horizontal scaling
- **Load Balancing** - Kubernetes-native load balancing
- **Auto Scaling** - HPA based on CPU/memory/custom metrics
- **Circuit Breakers** - Fault tolerance and graceful degradation

## 🛠️ Development

### Prerequisites
```bash
- Node.js 18+
- npm 8+
- Docker & Docker Compose
- Kubernetes cluster (for production)
```

### Local Development
```bash
# Clone and install
git clone <repository>
cd services/graphql-gateway
npm install

# Copy environment 
cp .env.example .env

# Start development server
npm run dev

# Build for production
npm run build
npm start
```

### Docker Development
```bash
# Build image
docker build -t selfmonitor/graphql-gateway .

# Run with docker-compose
docker-compose up -d

# Access GraphQL Playground
open http://localhost:4000/graphql
```

### Service URLs Configuration

Update `.env` with your service endpoints:

```env
# Core Services
AUTH_SERVICE_URL=http://auth-service:8080/graphql
USER_PROFILE_SERVICE_URL=http://user-profile-service:8080/graphql
TRANSACTIONS_SERVICE_URL=http://transactions-service:8080/graphql

# AI Services  
AI_AGENT_SERVICE_URL=http://ai-agent-service:8080/graphql
RECOMMENDATION_ENGINE_URL=http://recommendation-engine:8080/graphql

# Business Services
BUSINESS_INTELLIGENCE_URL=http://business-intelligence:8080/graphql
CUSTOMER_SUCCESS_URL=http://customer-success-platform:8080/graphql
```

## 📚 GraphQL Schema Examples

### Cross-Service Queries
```graphql
query UserDashboard {
  me {
    id
    email
    profile {
      firstName
      lastName
      avatar
    }
    transactions(filter: { startDate: "2024-01-01" }) {
      edges {
        node {
          id
          amount
          description
          category {
            name
          }
        }
      }
    }
    aiInsights {
      spendingPersonality {
        type
        characteristics
      }
      recommendations {
        title
        description
        priority
      }
    }
  }
}
```

### AI Agent Integration
```graphql
query AIChatSession {
  chatSessions(filter: { isActive: true }) {
    edges {
      node {
        id
        title
        messages {
          role
          content
          confidence
          timestamp
        }
        context {
          currentTopic
          intent
          urgency
        }
      }
    }
  }
}

mutation SendMessage {
  sendMessage(input: {
    sessionId: "session-123"
    content: "What's my spending pattern for restaurants?"
    messageType: TEXT
  }) {
    id
    content
    toolCalls {
      name
      arguments
      result
    }
    confidence
  }
}
```

### Automation Rules
```graphql
mutation CreateAutomation {
  createAutomationRule(input: {
    name: "Auto-categorize Uber rides"
    description: "Automatically categorize Uber transactions as Transportation"
    trigger: {
      type: EVENT_BASED
      events: [TRANSACTION_CREATED]
    }
    conditions: [{
      field: "merchantName"
      operator: CONTAINS
      value: "Uber"
    }]
    actions: [{
      type: CATEGORIZATION
      parameters: {
        categoryId: "transportation"
        subcategoryId: "rideshare" 
      }
    }]
  }) {
    id
    name
    isActive
    executionCount
  }
}
```

## 🔐 Security Implementation

### Authentication Flow
```typescript
// JWT token extraction and validation
const authHeader = req.headers.authorization;
const token = authHeader?.substring(7); // Remove 'Bearer '

const decoded = jwt.verify(token, JWT_SECRET);
return {
  user: {
    id: decoded.sub,
    email: decoded.email,
    roles: decoded.roles,
    tenantId: decoded.tenantId
  },
  authToken: token
};
```

### Authorization Headers
```typescript
// Automatic header forwarding to subgraphs
class AuthenticatedDataSource extends RemoteGraphQLDataSource {
  willSendRequest({ request, context }) {
    if (context.user) {
      request.http.headers.set('x-user-id', context.user.id);
      request.http.headers.set('x-user-roles', JSON.stringify(context.user.roles));
      request.http.headers.set('authorization', `Bearer ${context.authToken}`);
    }
  }
}
```

## 🚀 Deployment

### Kubernetes Deployment
```bash
# Apply Kubernetes manifests
kubectl apply -f infra/k8s/graphql-gateway.yaml

# Verify deployment
kubectl get pods -l app=graphql-gateway
kubectl get svc graphql-gateway

# Check logs
kubectl logs -f deployment/graphql-gateway
```

### Istio Integration
- **VirtualService** - Route `/graphql` to gateway
- **DestinationRule** - Load balancing and circuit breaking  
- **ServiceEntry** - External service configuration
- **Authorization Policy** - Fine-grained access control

### Environment Variables
```yaml
env:
- name: NODE_ENV
  value: "production"
- name: JWT_SECRET
  valueFrom:
    secretKeyRef:
      name: jwt-secret
      key: secret
- name: AUTH_SERVICE_URL
  value: "http://auth-service:8080/graphql"
```

## 📈 Monitoring & Observability

### Metrics Collection
- **Request Rate** - Operations per second
- **Request Duration** - P50, P95, P99 latencies  
- **Error Rate** - Error percentage by operation
- **Federation Metrics** - Subgraph performance

### Distributed Tracing
```typescript
// OpenTelemetry configuration
const sdk = new NodeSDK({
  traceExporter: jaegerExporter,
  instrumentations: [getNodeAutoInstrumentations()],
  serviceName: 'graphql-gateway'
});
```

### Log Structure
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info", 
  "message": "GraphQL Operation",
  "operationName": "UserDashboard",
  "userId": "user-123",
  "duration": 245,
  "complexity": 42
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Service Discovery Failures**
   ```bash
   # Check service endpoints
   kubectl get endpoints
   # Verify DNS resolution
   kubectl exec -it pod -- nslookup auth-service
   ```

2. **Schema Composition Errors**
   ```bash
   # Validate schema federation
   npm run validate-schema
   # Check subgraph health
   curl http://auth-service:8080/graphql -d '{"query":"{ __schema { types { name } } }"}'
   ```

3. **Authentication Issues**
   ```bash
   # Verify JWT secret
   echo $JWT_SECRET | base64 -d
   # Test token validation  
   curl -H "Authorization: Bearer $TOKEN" http://gateway:4000/graphql
   ```

### Performance Tuning
- Adjust `maxConnections` in connection pool
- Optimize query complexity limits
- Configure caching strategies
- Tune circuit breaker settings

## 📋 Roadmap

### Q1 2024
- [ ] Advanced caching with Redis
- [ ] Query complexity analysis
- [ ] Real-time subscriptions via GraphQL Subscriptions
- [ ] Federation 2.0 migration

### Q2 2024  
- [ ] Multi-region deployment
- [ ] Advanced security policies
- [ ] Performance optimization
- [ ] A/B testing integration

---

**Built with ❤️ for SelfMonitor FinTech Platform**

For more information, see:
- [Apollo Federation Documentation](https://www.apollographql.com/docs/federation/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
- [Microservices Architecture Guide](../docs/architecture/)