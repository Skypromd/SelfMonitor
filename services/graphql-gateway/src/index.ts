import { ApolloGateway, IntrospectAndCompose, RemoteGraphQLDataSource } from '@apollo/gateway';
import { ApolloServer } from 'apollo-server-express';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import jwt from 'jsonwebtoken';
import { createLogger, format, transports } from 'winston';
import dotenv from 'dotenv';

// Initialize tracing
import './tracing';

dotenv.config();

const logger = createLogger({
  level: 'info',
  format: format.combine(
    format.timestamp(),
    format.errors({ stack: true }),
    format.json()
  ),
  transports: [
    new transports.File({ filename: 'error.log', level: 'error' }),
    new transports.Console({ format: format.simple() })
  ]
});

// Authentication context extraction
interface AuthContext {
  user?: {
    id: string;
    email: string;
    roles: string[];
    tenantId?: string;
  };
  isAuthenticated: boolean;
}

// Custom data source with auth headers
class AuthenticatedDataSource extends RemoteGraphQLDataSource {
  willSendRequest({ request, context }: any) {
    if (context.user) {
      request.http.headers.set('x-user-id', context.user.id);
      request.http.headers.set('x-user-email', context.user.email);
      request.http.headers.set('x-user-roles', JSON.stringify(context.user.roles));
      if (context.user.tenantId) {
        request.http.headers.set('x-tenant-id', context.user.tenantId);
      }
    }
    
    // Forward authorization header
    if (context.authToken) {
      request.http.headers.set('authorization', `Bearer ${context.authToken}`);
    }
  }
}

// Gateway configuration
const gateway = new ApolloGateway({
  supergraphSdl: new IntrospectAndCompose({
    subgraphs: [
      // Core services
      { 
        name: 'auth-service', 
        url: process.env.AUTH_SERVICE_URL || 'http://auth-service:8080/graphql',
      },
      { 
        name: 'user-profile-service', 
        url: process.env.USER_PROFILE_SERVICE_URL || 'http://user-profile-service:8080/graphql',
      },
      { 
        name: 'transactions-service', 
        url: process.env.TRANSACTIONS_SERVICE_URL || 'http://transactions-service:8080/graphql',
      },
      { 
        name: 'analytics-service', 
        url: process.env.ANALYTICS_SERVICE_URL || 'http://analytics-service:8080/graphql',
      },
      { 
        name: 'advice-service', 
        url: process.env.ADVICE_SERVICE_URL || 'http://advice-service:8080/graphql',
      },
      { 
        name: 'categorization-service', 
        url: process.env.CATEGORIZATION_SERVICE_URL || 'http://categorization-service:8080/graphql',
      },
      { 
        name: 'banking-connector', 
        url: process.env.BANKING_CONNECTOR_URL || 'http://banking-connector:8080/graphql',
      },
      { 
        name: 'compliance-service', 
        url: process.env.COMPLIANCE_SERVICE_URL || 'http://compliance-service:8080/graphql',
      },
      { 
        name: 'documents-service', 
        url: process.env.DOCUMENTS_SERVICE_URL || 'http://documents-service:8080/graphql',
      },
      { 
        name: 'calendar-service', 
        url: process.env.CALENDAR_SERVICE_URL || 'http://calendar-service:8080/graphql',
      },
      
      // AI & ML services
      { 
        name: 'ai-agent-service', 
        url: process.env.AI_AGENT_SERVICE_URL || 'http://ai-agent-service:8080/graphql',
      },
      { 
        name: 'recommendation-engine', 
        url: process.env.RECOMMENDATION_ENGINE_URL || 'http://recommendation-engine:8080/graphql',
      },
      { 
        name: 'fraud-detection-service', 
        url: process.env.FRAUD_DETECTION_SERVICE_URL || 'http://fraud-detection-service:8080/graphql',
      },
      
      // Business services
      { 
        name: 'business-intelligence', 
        url: process.env.BUSINESS_INTELLIGENCE_URL || 'http://business-intelligence:8080/graphql',
      },
      { 
        name: 'customer-success-platform', 
        url: process.env.CUSTOMER_SUCCESS_URL || 'http://customer-success-platform:8080/graphql',
      },
      { 
        name: 'pricing-engine', 
        url: process.env.PRICING_ENGINE_URL || 'http://pricing-engine:8080/graphql',
      },
      
      // Integration services
      { 
        name: 'integrations-service', 
        url: process.env.INTEGRATIONS_SERVICE_URL || 'http://integrations-service:8080/graphql',
      },
      { 
        name: 'partner-registry', 
        url: process.env.PARTNER_REGISTRY_URL || 'http://partner-registry:8080/graphql',
      },
      { 
        name: 'payment-gateway', 
        url: process.env.PAYMENT_GATEWAY_URL || 'http://payment-gateway:8080/graphql',
      },
      
      // Core platform services  
      { 
        name: 'localization-service', 
        url: process.env.LOCALIZATION_SERVICE_URL || 'http://localization-service:8080/graphql',
      },
      { 
        name: 'consent-service', 
        url: process.env.CONSENT_SERVICE_URL || 'http://consent-service:8080/graphql',
      },
      { 
        name: 'tax-engine', 
        url: process.env.TAX_ENGINE_URL || 'http://tax-engine:8080/graphql',
      },
      { 
        name: 'qna-service', 
        url: process.env.QNA_SERVICE_URL || 'http://qna-service:8080/graphql',
      }
    ],
    pollIntervalInMs: 30000, // Poll for schema changes every 30 seconds
  }),
  buildService({ name, url }) {
    return new AuthenticatedDataSource({ url });
  },
});

const startServer = async () => {
  const app = express();
  
  // Security middleware
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'", "'unsafe-inline'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", "data:", "https:"],
      },
    },
  }));
  
  app.use(cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
    credentials: true,
  }));

  // Health check
  app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  const server = new ApolloServer({
    gateway,
    context: ({ req }): AuthContext => {
      const authHeader = req.headers.authorization;
      
      if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return { isAuthenticated: false };
      }
      
      const token = authHeader.substring(7);
      
      try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET || 'secret') as any;
        
        return {
          user: {
            id: decoded.sub,
            email: decoded.email,
            roles: decoded.roles || [],
            tenantId: decoded.tenantId,
          },
          isAuthenticated: true,
          authToken: token,
        };
      } catch (error) {
        logger.warn('Invalid JWT token', { error: error.message });
        return { isAuthenticated: false };
      }
    },
    introspection: process.env.NODE_ENV !== 'production',
    plugins: [
      {
        requestDidStart() {
          return {
            didResolveOperation({ request, operationName }) {
              logger.info('GraphQL Operation', {
                operationName,
                query: request.query?.substring(0, 200) + '...',
              });
            },
            didEncounterErrors({ errors }) {
              logger.error('GraphQL Errors', { 
                errors: errors.map(err => ({
                  message: err.message,
                  path: err.path,
                  locations: err.locations,
                }))
              });
            },
          };
        },
      },
    ],
  });

  await server.start();
  server.applyMiddleware({ app, path: '/graphql' });

  const PORT = process.env.PORT || 4000;
  
  app.listen(PORT, () => {
    logger.info(`🚀 GraphQL Gateway ready at http://localhost:${PORT}${server.graphqlPath}`, {
      port: PORT,
      graphqlPath: server.graphqlPath,
      environment: process.env.NODE_ENV || 'development',
    });
  });
};

// Graceful shutdown
process.on('SIGINT', () => {
  logger.info('Received SIGINT, shutting down gracefully');
  process.exit(0);
});

process.on('SIGTERM', () => {
  logger.info('Received SIGTERM, shutting down gracefully');
  process.exit(0);
});

// Start the server
startServer().catch(error => {
  logger.error('Failed to start server', { error: error.message, stack: error.stack });
  process.exit(1);
});