import Fastify, { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import helmet from '@fastify/helmet';
import cors from '@fastify/cors';
import rateLimit from '@fastify/rate-limit';
import jwt from '@fastify/jwt';
import session from '@fastify/session';
import swagger from '@fastify/swagger';
import swaggerUi from '@fastify/swagger-ui';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { JaegerExporter } from '@opentelemetry/exporter-jaeger';
import winston from 'winston';
import ElasticsearchTransport from 'winston-elasticsearch';
import bcrypt from 'bcrypt';
import speakeasy from 'speakeasy';
import qrcode from 'qrcode';
import { Pool } from 'pg';
import Redis from 'redis';
import { v4 as uuidv4 } from 'uuid';
import UAParser from 'ua-parser-js';
import geoip from 'geoip-lite';
import { DeviceDetector } from 'device-detector-js';
import * as crypto from 'crypto';

// Initialize OpenTelemetry
const sdk = new NodeSDK({
  traceExporter: new JaegerExporter({
    endpoint: process.env.JAEGER_ENDPOINT || 'http://localhost:14268/api/traces',
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();

// Initialize logger with SIEM integration
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json(),
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/security-error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/security-audit.log', level: 'warn' }),
    new winston.transports.File({ filename: 'logs/security-info.log' }),
  ],
});

// Add Elasticsearch SIEM integration if configured
if (process.env.ELASTICSEARCH_URL) {
  logger.add(
    new ElasticsearchTransport({
      level: 'info',
      clientOpts: { node: process.env.ELASTICSEARCH_URL },
      index: 'selfmonitor-security-logs',
      typeName: 'security_event',
    }),
  );
}

// Database connection
const pool = new Pool({
  connectionString: process.env.SECURITY_DATABASE_URL || 'postgresql://localhost:5432/security',
});

// Redis connection for session management and caching
const redisClient = Redis.createClient({
  url: process.env.SECURITY_REDIS_URL || 'redis://localhost:6379/3',
});

// Security configuration
const SECURITY_CONFIG = {
  jwt: {
    secret: process.env.JWT_SECRET_KEY || 'super-secret-jwt-key-change-in-production',
    expiresIn: '15m', // Short-lived for security
  },
  mfa: {
    issuer: process.env.MFA_ISSUER || 'SelfMonitor',
    window: 2, // Allow 2 time windows for TOTP
  },
  session: {
    maxIdleTime: 30 * 60 * 1000, // 30 minutes
    maxSessionTime: 8 * 60 * 60 * 1000, // 8 hours
  },
  rateLimit: {
    global: 1000, // per minute
    perUser: 100, // per minute
    perIP: 500, // per minute
    loginAttempts: 5, // max failed attempts
    lockoutDuration: 5 * 60 * 1000, // 5 minutes
  },
  passwordPolicy: {
    minLength: 12,
    requireSpecialChars: true,
    requireNumbers: true,
    requireUppercase: true,
    passwordHistory: 12,
  },
  compliance: {
    auditLogRetention: 2555, // days (7 years)
    encryptionAlgorithm: 'AES-256-GCM',
    keyRotation: 90, // days
  },
};

// Types for security events and threat detection
interface SecurityEvent {
  id: string;
  userId?: string;
  sessionId?: string;
  eventType: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  ipAddress: string;
  userAgent: string;
  location?: any;
  deviceInfo?: any;
  timestamp: Date;
  metadata?: any;
}

interface ThreatIndicator {
  type: 'ip' | 'domain' | 'hash' | 'email' | 'user_behavior';
  value: string;
  confidence: number;
  source: string;
  description: string;
  threat_types: string[];
  first_seen: Date;
  last_seen: Date;
}

interface ComplianceCheck {
  id: string;
  checkType: 'soc2' | 'iso27001' | 'gdpr' | 'pci_dss' | 'custom';
  controlId: string;
  status: 'pass' | 'fail' | 'warning' | 'not_applicable';
  description: string;
  evidence?: string[];
  remediationSteps?: string[];
  dueDate?: Date;
  assignee?: string;
  lastChecked: Date;
}

// Security Service Class
class SecurityService {
  private app: FastifyInstance;
  private threatDetector: ThreatDetectionEngine;
  private complianceManager: ComplianceManager;
  private siemEngine: SIEMEngine;
  private authManager: ZeroTrustAuthManager;

  constructor() {
    this.app = Fastify({ logger: true });
    this.threatDetector = new ThreatDetectionEngine();
    this.complianceManager = new ComplianceManager();
    this.siemEngine = new SIEMEngine();
    this.authManager = new ZeroTrustAuthManager();
  }

  public async initialize(): Promise<void> {
    await this.setupMiddleware();
    await this.setupRoutes();
    await this.initializeDatabase();
    await this.initializeRedis();
  }

  private async setupMiddleware(): Promise<void> {
    // Security headers
    await this.app.register(helmet, {
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'"],
          imgSrc: ["'self'", 'data:', 'https:'],
        },
      },
    });

    // CORS configuration
    await this.app.register(cors, {
      origin: (origin, callback) => {
        const allowedOrigins = (process.env.ALLOWED_ORIGINS || 'https://app.selfmonitor.com').split(',');
        if (!origin || allowedOrigins.includes(origin)) {
          callback(null, true);
        } else {
          callback(new Error('Not allowed by CORS'), false);
        }
      },
      credentials: true,
    });

    // Rate limiting with advanced configuration
    await this.app.register(rateLimit, {
      global: true,
      max: SECURITY_CONFIG.rateLimit.global,
      timeWindow: '1 minute',
      keyGenerator: (req: FastifyRequest) => {
        const userId = req.user?.id || 'anonymous';
        const ipAddress = req.ip;
        return `${userId}:${ipAddress}`;
      },
      onExceeded: async (req: FastifyRequest, reply: FastifyReply) => {
        await this.siemEngine.logSecurityEvent({
          eventType: 'rate_limit_exceeded',
          severity: 'medium',
          description: 'Rate limit exceeded',
          ipAddress: req.ip,
          userAgent: req.headers['user-agent'] || '',
          userId: req.user?.id,
        });
        reply.code(429).send({ error: 'Rate limit exceeded' });
      },
    });

    // JWT authentication
    await this.app.register(jwt, {
      secret: SECURITY_CONFIG.jwt.secret,
      sign: { expiresIn: SECURITY_CONFIG.jwt.expiresIn },
    });

    // Session management
    await this.app.register(session, {
      secret: process.env.SESSION_SECRET || 'session-secret-change-in-production',
      cookieName: 'sessionId',
      cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        maxAge: SECURITY_CONFIG.session.maxSessionTime,
        sameSite: 'strict',
      },
      store: {
        set: async (sessionId: string, session: any, ttl: number) => {
          await redisClient.setEx(`session:${sessionId}`, ttl, JSON.stringify(session));
        },
        get: async (sessionId: string) => {
          const session = await redisClient.get(`session:${sessionId}`);
          return session ? JSON.parse(session) : null;
        },
        destroy: async (sessionId: string) => {
          await redisClient.del(`session:${sessionId}`);
        },
      },
    });

    // API documentation
    await this.app.register(swagger, {
      routePrefix: '/documentation',
      swagger: {
        info: {
          title: 'Security Service API',
          description: 'Enterprise security management and monitoring API',
          version: '1.0.0',
        },
        host: 'localhost:8018',
        schemes: ['http', 'https'],
        consumes: ['application/json'],
        produces: ['application/json'],
        securityDefinitions: {
          apiKey: {
            type: 'apiKey',
            name: 'authorization',
            in: 'header',
          },
        },
      },
      exposeRoute: true,
    });

    await this.app.register(swaggerUi, {
      routePrefix: '/documentation',
      uiConfig: {
        docExpansion: 'full',
        deepLinking: false,
      },
    });
  }

  private async setupRoutes(): Promise<void> {
    // Health check endpoint
    this.app.get('/health', {
      schema: {
        description: 'Health check endpoint',
        response: {
          200: {
            type: 'object',
            properties: {
              status: { type: 'string' },
              timestamp: { type: 'string' },
              services: { type: 'object' },
            },
          },
        },
      },
    }, async (request, reply) => {
      const health = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
          database: await this.checkDatabaseHealth(),
          redis: await this.checkRedisHealth(),
          siem: await this.siemEngine.checkHealth(),
          threatDetection: await this.threatDetector.checkHealth(),
        },
      };
      return health;
    });

    // Authentication endpoints
    this.app.post('/auth/login', {
      schema: {
        description: 'User login with optional MFA',
        body: {
          type: 'object',
          required: ['email', 'password'],
          properties: {
            email: { type: 'string', format: 'email' },
            password: { type: 'string' },
            mfaToken: { type: 'string' },
            deviceFingerprint: { type: 'string' },
          },
        },
      },
    }, async (request, reply) => {
      return await this.authManager.handleLogin(request, reply);
    });

    this.app.post('/auth/logout', {
      preHandler: [this.authManager.authenticateToken],
    }, async (request, reply) => {
      return await this.authManager.handleLogout(request, reply);
    });

    this.app.post('/auth/mfa/setup', {
      preHandler: [this.authManager.authenticateToken],
    }, async (request, reply) => {
      return await this.authManager.setupMFA(request, reply);
    });

    this.app.post('/auth/mfa/verify', {
      preHandler: [this.authManager.authenticateToken],
    }, async (request, reply) => {
      return await this.authManager.verifyMFA(request, reply);
    });

    // Security monitoring endpoints
    this.app.get('/security/events', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('security_admin')],
    }, async (request, reply) => {
      return await this.siemEngine.getSecurityEvents(request.query);
    });

    this.app.post('/security/events', {
      preHandler: [this.authManager.authenticateToken],
      schema: {
        body: {
          type: 'object',
          required: ['eventType', 'severity', 'description'],
          properties: {
            eventType: { type: 'string' },
            severity: { type: 'string', enum: ['low', 'medium', 'high', 'critical'] },
            description: { type: 'string' },
            metadata: { type: 'object' },
          },
        },
      },
    }, async (request, reply) => {
      return await this.siemEngine.logSecurityEvent({
        ...request.body,
        userId: request.user.id,
        ipAddress: request.ip,
        userAgent: request.headers['user-agent'] || '',
      });
    });

    // Threat detection endpoints
    this.app.get('/security/threats', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('security_admin')],
    }, async (request, reply) => {
      return await this.threatDetector.getThreats(request.query);
    });

    this.app.post('/security/threats/analyze', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('security_admin')],
    }, async (request, reply) => {
      return await this.threatDetector.analyzeThreat(request.body);
    });

    // Compliance endpoints
    this.app.get('/compliance/checks', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('compliance_admin')],
    }, async (request, reply) => {
      return await this.complianceManager.getComplianceChecks(request.query);
    });

    this.app.post('/compliance/checks', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('compliance_admin')],
    }, async (request, reply) => {
      return await this.complianceManager.runComplianceCheck(request.body);
    });

    this.app.get('/compliance/reports/:type', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('compliance_admin')],
    }, async (request, reply) => {
      const { type } = request.params as { type: string };
      return await this.complianceManager.generateComplianceReport(type, request.query);
    });

    // Security dashboard endpoints
    this.app.get('/security/dashboard', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('security_admin')],
    }, async (request, reply) => {
      return await this.siemEngine.getSecurityDashboard();
    });

    this.app.get('/security/metrics', {
      preHandler: [this.authManager.authenticateToken, this.authManager.requireRole('security_admin')],
    }, async (request, reply) => {
      return await this.siemEngine.getSecurityMetrics(request.query);
    });
  }

  private async initializeDatabase(): Promise<void> {
    // Create security tables if they don't exist
    await pool.query(`
      CREATE SCHEMA IF NOT EXISTS security;
      
      CREATE TABLE IF NOT EXISTS security.events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID,
        session_id VARCHAR(255),
        event_type VARCHAR(100) NOT NULL,
        severity VARCHAR(20) NOT NULL,
        description TEXT NOT NULL,
        ip_address INET NOT NULL,
        user_agent TEXT,
        location JSONB,
        device_info JSONB,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        INDEX idx_events_user_id (user_id),
        INDEX idx_events_event_type (event_type),
        INDEX idx_events_severity (severity),
        INDEX idx_events_created_at (created_at),
        INDEX idx_events_ip_address (ip_address)
      );

      CREATE TABLE IF NOT EXISTS security.threat_indicators (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        type VARCHAR(50) NOT NULL,
        value TEXT NOT NULL,
        confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
        source VARCHAR(255) NOT NULL,
        description TEXT,
        threat_types TEXT[],
        first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        INDEX idx_threats_type (type),
        INDEX idx_threats_value (value),
        INDEX idx_threats_confidence (confidence),
        INDEX idx_threats_source (source),
        INDEX idx_threats_active (is_active)
      );

      CREATE TABLE IF NOT EXISTS security.compliance_checks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        check_type VARCHAR(50) NOT NULL,
        control_id VARCHAR(100) NOT NULL,
        status VARCHAR(20) NOT NULL,
        description TEXT NOT NULL,
        evidence TEXT[],
        remediation_steps TEXT[],
        due_date TIMESTAMP WITH TIME ZONE,
        assignee VARCHAR(255),
        last_checked TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        INDEX idx_compliance_type (check_type),
        INDEX idx_compliance_status (status),
        INDEX idx_compliance_due_date (due_date),
        INDEX idx_compliance_assignee (assignee)
      );

      CREATE TABLE IF NOT EXISTS security.user_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL,
        session_token VARCHAR(255) UNIQUE NOT NULL,
        ip_address INET NOT NULL,
        user_agent TEXT,
        device_fingerprint TEXT,
        location JSONB,
        is_active BOOLEAN DEFAULT TRUE,
        last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        INDEX idx_sessions_user_id (user_id),
        INDEX idx_sessions_token (session_token),
        INDEX idx_sessions_active (is_active),
        INDEX idx_sessions_expires_at (expires_at)
      );

      CREATE TABLE IF NOT EXISTS security.mfa_secrets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL UNIQUE,
        secret VARCHAR(255) NOT NULL,
        backup_codes TEXT[],
        is_enabled BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        INDEX idx_mfa_user_id (user_id)
      );
    `);

    logger.info('Security database initialized successfully');
  }

  private async initializeRedis(): Promise<void> {
    await redisClient.connect();
    logger.info('Redis connection established for security service');
  }

  private async checkDatabaseHealth(): Promise<string> {
    try {
      await pool.query('SELECT NOW()');
      return 'healthy';
    } catch (error) {
      logger.error('Database health check failed:', error);
      return 'unhealthy';
    }
  }

  private async checkRedisHealth(): Promise<string> {
    try {
      await redisClient.ping();
      return 'healthy';
    } catch (error) {
      logger.error('Redis health check failed:', error);
      return 'unhealthy';
    }
  }

  public async start(): Promise<void> {
    try {
      await this.initialize();
      const port = parseInt(process.env.SECURITY_SERVICE_PORT || '8018', 10);
      await this.app.listen({ port, host: '0.0.0.0' });
      logger.info(`Security Service started on port ${port}`);
    } catch (error) {
      logger.error('Failed to start security service:', error);
      process.exit(1);
    }
  }

  public async stop(): Promise<void> {
    await this.app.close();
    await pool.end();
    await redisClient.disconnect();
    logger.info('Security Service stopped');
  }
}

// Export classes for testing and external use
export { SecurityService };

// Start the service if this file is run directly
if (require.main === module) {
  const securityService = new SecurityService();
  process.on('SIGTERM', () => securityService.stop());
  process.on('SIGINT', () => securityService.stop());
  securityService.start();
}

// Import additional security modules (to be created in separate files)
import { ThreatDetectionEngine } from './modules/threat-detection';
import { ComplianceManager } from './modules/compliance';
import { SIEMEngine } from './modules/siem';
import { ZeroTrustAuthManager } from './modules/zero-trust-auth';