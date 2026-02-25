import { FastifyRequest, FastifyReply } from 'fastify';
import { Pool } from 'pg';
import Redis from 'redis';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import speakeasy from 'speakeasy';
import qrcode from 'qrcode';
import crypto from 'crypto';
import UAParser from 'ua-parser-js';
import geoip from 'geoip-lite';
import { DeviceDetector } from 'device-detector-js';
import winston from 'winston';
import { v4 as uuidv4 } from 'uuid';

export interface User {
  id: string;
  email: string;
  passwordHash: string;
  roles: string[];
  isActive: boolean;
  isMfaEnabled: boolean;
  lastLogin?: Date;
  failedLoginAttempts: number;
  lockedUntil?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface UserSession {
  id: string;
  userId: string;
  sessionToken: string;
  ipAddress: string;
  userAgent: string;
  deviceFingerprint: string;
  location: any;
  isActive: boolean;
  lastActivity: Date;
  createdAt: Date;
  expiresAt: Date;
}

export interface AuthenticationResult {
  success: boolean;
  user?: User;
  token?: string;
  refreshToken?: string;
  requiresMfa?: boolean;
  mfaSecret?: string;
  qrCodeUrl?: string;
  session?: UserSession;
  error?: string;
  riskScore?: number;
}

export interface RiskAssessment {
  score: number; // 0-100, higher means more risky
  factors: string[];
  action: 'allow' | 'challenge' | 'block';
  reason: string;
}

/**
 * Zero-Trust Authentication Manager
 * 
 * Implements comprehensive zero-trust authentication including:
 * - Multi-factor authentication (MFA)
 * - Risk-based authentication
 * - Device fingerprinting
 * - Session management
 * - Behavioral analysis
 */
export class ZeroTrustAuthManager {
  private pool: Pool;
  private redis: Redis.RedisClientType;
  private logger: winston.Logger;
  private deviceDetector: DeviceDetector;

  // Configuration constants
  private readonly JWT_SECRET = process.env.JWT_SECRET_KEY || 'super-secret-jwt-key-change-in-production';
  private readonly JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '15m';
  private readonly REFRESH_TOKEN_EXPIRES_IN = '7d';
  private readonly SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes
  private readonly MAX_FAILED_ATTEMPTS = 5;
  private readonly LOCKOUT_DURATION = 15 * 60 * 1000; // 15 minutes
  private readonly HIGH_RISK_THRESHOLD = 75;
  private readonly MEDIUM_RISK_THRESHOLD = 50;

  constructor() {
    this.pool = new Pool({
      connectionString: process.env.SECURITY_DATABASE_URL || 'postgresql://localhost:5432/security',
    });
    this.redis = Redis.createClient({
      url: process.env.SECURITY_REDIS_URL || 'redis://localhost:6379/3',
    });
    this.deviceDetector = new DeviceDetector();
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json(),
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/auth.log' }),
      ],
    });
  }

  /**
   * Handle user login with zero-trust verification
   */
  public async handleLogin(request: FastifyRequest, reply: FastifyReply): Promise<AuthenticationResult> {
    const { email, password, mfaToken, deviceFingerprint } = request.body as any;
    const ipAddress = request.ip;
    const userAgent = request.headers['user-agent'] || '';

    try {
      // Step 1: Basic credential validation
      const user = await this.validateCredentials(email, password);
      if (!user.success || !user.user) {
        await this.logSecurityEvent('login_failed', {
          email,
          ipAddress,
          userAgent,
          reason: 'invalid_credentials',
        });
        return { success: false, error: 'Invalid credentials' };
      }

      // Step 2: Check if account is locked
      if (user.user.lockedUntil && user.user.lockedUntil > new Date()) {
        await this.logSecurityEvent('login_blocked', {
          userId: user.user.id,
          email,
          ipAddress,
          userAgent,
          reason: 'account_locked',
        });
        return { success: false, error: 'Account is temporarily locked' };
      }

      // Step 3: Risk-based authentication
      const riskAssessment = await this.assessLoginRisk(user.user, {
        ipAddress,
        userAgent,
        deviceFingerprint,
      });

      // Step 4: MFA validation (if enabled or required by risk)
      if (user.user.isMfaEnabled || riskAssessment.action === 'challenge') {
        if (!mfaToken) {
          return {
            success: false,
            requiresMfa: true,
            error: 'MFA token required',
            riskScore: riskAssessment.score,
          };
        }

        const mfaValid = await this.validateMFA(user.user.id, mfaToken);
        if (!mfaValid) {
          await this.logSecurityEvent('mfa_failed', {
            userId: user.user.id,
            email,
            ipAddress,
            userAgent,
            reason: 'invalid_mfa_token',
          });
          return { success: false, error: 'Invalid MFA token' };
        }
      }

      // Step 5: Block if risk is too high
      if (riskAssessment.action === 'block') {
        await this.logSecurityEvent('login_blocked', {
          userId: user.user.id,
          email,
          ipAddress,
          userAgent,
          reason: 'high_risk',
          riskScore: riskAssessment.score,
        });
        return { 
          success: false, 
          error: 'Login blocked due to security concerns',
          riskScore: riskAssessment.score,
        };
      }

      // Step 6: Create session and tokens
      const session = await this.createSession(user.user, {
        ipAddress,
        userAgent,
        deviceFingerprint: deviceFingerprint || this.generateDeviceFingerprint(userAgent),
      });

      const tokens = await this.generateTokens(user.user, session);

      // Step 7: Update user login information
      await this.updateUserLoginInfo(user.user.id, ipAddress);

      // Step 8: Reset failed attempts counter
      await this.resetFailedAttempts(user.user.id);

      await this.logSecurityEvent('login_success', {
        userId: user.user.id,
        email,
        ipAddress,
        userAgent,
        sessionId: session.id,
        riskScore: riskAssessment.score,
      });

      return {
        success: true,
        user: user.user,
        token: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        session,
        riskScore: riskAssessment.score,
      };

    } catch (error) {
      this.logger.error('Login error:', error);
      await this.logSecurityEvent('login_error', {
        email,
        ipAddress,
        userAgent,
        error: error.message,
      });
      return { success: false, error: 'Internal server error' };
    }
  }

  /**
   * Handle user logout
   */
  public async handleLogout(request: FastifyRequest, reply: FastifyReply): Promise<{ success: boolean }> {
    try {
      const sessionToken = this.extractTokenFromRequest(request);
      if (sessionToken) {
        await this.revokeSession(sessionToken);
        await this.logSecurityEvent('logout_success', {
          userId: request.user?.id,
          ipAddress: request.ip,
          userAgent: request.headers['user-agent'] || '',
        });
      }

      reply.clearCookie('sessionId');
      return { success: true };
    } catch (error) {
      this.logger.error('Logout error:', error);
      return { success: false };
    }
  }

  /**
   * Setup MFA for user
   */
  public async setupMFA(request: FastifyRequest, reply: FastifyReply): Promise<{
    success: boolean;
    secret?: string;
    qrCodeUrl?: string;
    backupCodes?: string[];
    error?: string;
  }> {
    try {
      const userId = request.user?.id;
      if (!userId) {
        return { success: false, error: 'User not authenticated' };
      }

      // Generate MFA secret
      const secret = speakeasy.generateSecret({
        name: `SelfMonitor (${request.user.email})`,
        issuer: process.env.MFA_ISSUER || 'SelfMonitor',
        length: 32,
      });

      // Generate backup codes
      const backupCodes = Array.from({ length: 8 }, () => 
        crypto.randomBytes(4).toString('hex').toUpperCase()
      );

      // Generate QR code
      const qrCodeUrl = await qrcode.toDataURL(secret.otpauth_url!);

      // Store MFA secret (not yet enabled)
      await this.pool.query(`
        INSERT INTO security.mfa_secrets (user_id, secret, backup_codes, is_enabled)
        VALUES ($1, $2, $3, false)
        ON CONFLICT (user_id) 
        UPDATE SET secret = $2, backup_codes = $3, is_enabled = false, updated_at = NOW()
      `, [userId, secret.base32, backupCodes]);

      await this.logSecurityEvent('mfa_setup', {
        userId,
        ipAddress: request.ip,
        userAgent: request.headers['user-agent'] || '',
      });

      return {
        success: true,
        secret: secret.base32,
        qrCodeUrl,
        backupCodes,
      };
    } catch (error) {
      this.logger.error('MFA setup error:', error);
      return { success: false, error: 'Failed to setup MFA' };
    }
  }

  /**
   * Verify and enable MFA
   */
  public async verifyMFA(request: FastifyRequest, reply: FastifyReply): Promise<{
    success: boolean;
    enabled?: boolean;
    error?: string;
  }> {
    try {
      const { token } = request.body as { token: string };
      const userId = request.user?.id;

      if (!userId || !token) {
        return { success: false, error: 'Missing required parameters' };
      }

      // Get MFA secret
      const mfaResult = await this.pool.query(
        'SELECT secret FROM security.mfa_secrets WHERE user_id = $1',
        [userId]
      );

      if (mfaResult.rows.length === 0) {
        return { success: false, error: 'MFA not setup' };
      }

      const secret = mfaResult.rows[0].secret;

      // Verify token
      const verified = speakeasy.totp.verify({
        secret,
        encoding: 'base32',
        token,
        window: 2, // Allow 2 time windows for clock skew
      });

      if (!verified) {
        await this.logSecurityEvent('mfa_verification_failed', {
          userId,
          ipAddress: request.ip,
          userAgent: request.headers['user-agent'] || '',
        });
        return { success: false, error: 'Invalid MFA token' };
      }

      // Enable MFA
      await this.pool.query(`
        UPDATE security.mfa_secrets 
        SET is_enabled = true, updated_at = NOW() 
        WHERE user_id = $1
      `, [userId]);

      await this.pool.query(`
        UPDATE users 
        SET is_mfa_enabled = true, updated_at = NOW() 
        WHERE id = $1
      `, [userId]);

      await this.logSecurityEvent('mfa_enabled', {
        userId,
        ipAddress: request.ip,
        userAgent: request.headers['user-agent'] || '',
      });

      return { success: true, enabled: true };
    } catch (error) {
      this.logger.error('MFA verification error:', error);
      return { success: false, error: 'Failed to verify MFA' };
    }
  }

  /**
   * Middleware to authenticate JWT tokens
   */
  public async authenticateToken(request: FastifyRequest, reply: FastifyReply): Promise<void> {
    try {
      const token = this.extractTokenFromRequest(request);
      if (!token) {
        reply.code(401).send({ error: 'Access token required' });
        return;
      }

      // Verify JWT token
      const decoded = jwt.verify(token, this.JWT_SECRET) as any;
      
      // Check if session is still valid
      const session = await this.getValidSession(decoded.sessionId);
      if (!session) {
        reply.code(401).send({ error: 'Session expired or invalid' });
        return;
      }

      // Update session activity
      await this.updateSessionActivity(session.id, request.ip);

      // Get user information
      const userResult = await this.pool.query(
        'SELECT * FROM users WHERE id = $1 AND is_active = true',
        [decoded.userId]
      );

      if (userResult.rows.length === 0) {
        reply.code(401).send({ error: 'User not found or inactive' });
        return;
      }

      // Attach user to request
      request.user = {
        id: decoded.userId,
        email: decoded.email,
        roles: decoded.roles || [],
        sessionId: session.id,
      };

      await this.logSecurityEvent('token_validated', {
        userId: decoded.userId,
        sessionId: session.id,
        ipAddress: request.ip,
        userAgent: request.headers['user-agent'] || '',
      });

    } catch (error) {
      this.logger.error('Token authentication error:', error);
      
      if (error.name === 'JsonWebTokenError') {
        reply.code(401).send({ error: 'Invalid token' });
      } else if (error.name === 'TokenExpiredError') {
        reply.code(401).send({ error: 'Token expired' });
      } else {
        reply.code(500).send({ error: 'Authentication error' });
      }
    }
  }

  /**
   * Middleware to require specific roles
   */
  public requireRole(requiredRole: string) {
    return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
      if (!request.user) {
        reply.code(401).send({ error: 'Authentication required' });
        return;
      }

      if (!request.user.roles.includes(requiredRole) && !request.user.roles.includes('admin')) {
        await this.logSecurityEvent('authorization_failed', {
          userId: request.user.id,
          requiredRole,
          userRoles: request.user.roles,
          ipAddress: request.ip,
          userAgent: request.headers['user-agent'] || '',
        });
        reply.code(403).send({ error: `Role '${requiredRole}' required` });
        return;
      }
    };
  }

  /**
   * Validate user credentials
   */
  private async validateCredentials(email: string, password: string): Promise<{
    success: boolean;
    user?: User;
  }> {
    const userResult = await this.pool.query(
      'SELECT * FROM users WHERE email = $1',
      [email.toLowerCase()]
    );

    if (userResult.rows.length === 0) {
      // Increment failed attempts even for non-existent users to prevent enumeration
      await this.incrementFailedAttempts(email);
      return { success: false };
    }

    const user = userResult.rows[0];

    if (!user.is_active) {
      return { success: false };
    }

    const passwordValid = await bcrypt.compare(password, user.password_hash);
    if (!passwordValid) {
      await this.incrementFailedAttempts(user.id);
      return { success: false };
    }

    return { success: true, user: this.mapDatabaseRowToUser(user) };
  }

  /**
   * Assess login risk based on various factors
   */
  private async assessLoginRisk(user: User, context: {
    ipAddress: string;
    userAgent: string;
    deviceFingerprint?: string;
  }): Promise<RiskAssessment> {
    const factors: string[] = [];
    let riskScore = 0;

    // Check IP reputation and geolocation
    const locationInfo = geoip.lookup(context.ipAddress);
    if (locationInfo) {
      // Check if login from new country
      const recentLogins = await this.pool.query(`
        SELECT DISTINCT metadata->'location'->>'country' as country
        FROM security.events
        WHERE user_id = $1 AND event_type = 'login_success'
        AND created_at > NOW() - INTERVAL '30 days'
      `, [user.id]);

      const knownCountries = recentLogins.rows.map(row => row.country).filter(Boolean);
      if (knownCountries.length > 0 && !knownCountries.includes(locationInfo.country)) {
        riskScore += 30;
        factors.push('login_from_new_country');
      }

      // Check for high-risk countries (simplified list)
      const highRiskCountries = ['CN', 'RU', 'KP', 'IR'];
      if (highRiskCountries.includes(locationInfo.country)) {
        riskScore += 20;
        factors.push('login_from_high_risk_country');
      }
    }

    // Check device fingerprint
    if (context.deviceFingerprint) {
      const knownDevices = await this.pool.query(`
        SELECT COUNT(*) FROM security.user_sessions
        WHERE user_id = $1 AND device_fingerprint = $2
        AND created_at > NOW() - INTERVAL '90 days'
      `, [user.id, context.deviceFingerprint]);

      if (parseInt(knownDevices.rows[0].count, 10) === 0) {
        riskScore += 25;
        factors.push('login_from_new_device');
      }
    }

    // Check time-based patterns
    const currentHour = new Date().getHours();
    const recentLoginHours = await this.pool.query(`
      SELECT EXTRACT(HOUR FROM created_at) as hour, COUNT(*) as count
      FROM security.events
      WHERE user_id = $1 AND event_type = 'login_success'
      AND created_at > NOW() - INTERVAL '30 days'
      GROUP BY EXTRACT(HOUR FROM created_at)
      ORDER BY count DESC
    `, [user.id]);

    const normalHours = recentLoginHours.rows.slice(0, 3).map(row => parseInt(row.hour, 10));
    if (normalHours.length > 0 && !normalHours.some(hour => Math.abs(hour - currentHour) <= 2)) {
      riskScore += 15;
      factors.push('login_at_unusual_time');
    }

    // Check for recent failed attempts
    const recentFailures = await this.pool.query(`
      SELECT COUNT(*) FROM security.events
      WHERE user_id = $1 AND event_type = 'login_failed'
      AND created_at > NOW() - INTERVAL '1 hour'
    `, [user.id]);

    const failureCount = parseInt(recentFailures.rows[0].count, 10);
    if (failureCount > 3) {
      riskScore += 20;
      factors.push('recent_failed_attempts');
    }

    // Check user agent changes
    const recentUserAgents = await this.pool.query(`
      SELECT DISTINCT user_agent
      FROM security.events
      WHERE user_id = $1 AND event_type = 'login_success'
      AND created_at > NOW() - INTERVAL '7 days'
      LIMIT 5
    `, [user.id]);

    const knownUserAgents = recentUserAgents.rows.map(row => row.user_agent);
    if (knownUserAgents.length > 0 && !knownUserAgents.includes(context.userAgent)) {
      riskScore += 10;
      factors.push('login_with_new_user_agent');
    }

    // Determine action based on risk score
    let action: 'allow' | 'challenge' | 'block';
    let reason: string;

    if (riskScore >= this.HIGH_RISK_THRESHOLD) {
      action = 'block';
      reason = 'High risk score detected';
    } else if (riskScore >= this.MEDIUM_RISK_THRESHOLD || !user.isMfaEnabled) {
      action = 'challenge';
      reason = 'Medium risk score or MFA required';
    } else {
      action = 'allow';
      reason = 'Low risk score';
    }

    return {
      score: Math.min(riskScore, 100),
      factors,
      action,
      reason,
    };
  }

  /**
   * Validate MFA token
   */
  private async validateMFA(userId: string, token: string): Promise<boolean> {
    const mfaResult = await this.pool.query(
      'SELECT secret, backup_codes FROM security.mfa_secrets WHERE user_id = $1 AND is_enabled = true',
      [userId]
    );

    if (mfaResult.rows.length === 0) {
      return false;
    }

    const { secret, backup_codes } = mfaResult.rows[0];

    // First try TOTP validation
    const verified = speakeasy.totp.verify({
      secret,
      encoding: 'base32',
      token,
      window: 2,
    });

    if (verified) {
      return true;
    }

    // Try backup codes
    if (backup_codes && backup_codes.includes(token.toUpperCase())) {
      // Remove used backup code
      const updatedCodes = backup_codes.filter((code: string) => code !== token.toUpperCase());
      await this.pool.query(
        'UPDATE security.mfa_secrets SET backup_codes = $1, updated_at = NOW() WHERE user_id = $2',
        [updatedCodes, userId]
      );
      return true;
    }

    return false;
  }

  /**
   * Create user session
   */
  private async createSession(user: User, context: {
    ipAddress: string;
    userAgent: string;
    deviceFingerprint: string;
  }): Promise<UserSession> {
    const sessionId = uuidv4();
    const sessionToken = crypto.randomBytes(32).toString('hex');
    const expiresAt = new Date(Date.now() + 8 * 60 * 60 * 1000); // 8 hours

    const locationInfo = geoip.lookup(context.ipAddress);
    const deviceInfo = this.deviceDetector.parse(context.userAgent);

    await this.pool.query(`
      INSERT INTO security.user_sessions (
        id, user_id, session_token, ip_address, user_agent, 
        device_fingerprint, location, expires_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    `, [
      sessionId,
      user.id,
      sessionToken,
      context.ipAddress,
      context.userAgent,
      context.deviceFingerprint,
      JSON.stringify(locationInfo),
      expiresAt,
    ]);

    // Store session in Redis for fast access
    await this.redis.setEx(
      `session:${sessionToken}`,
      8 * 60 * 60, // 8 hours
      JSON.stringify({
        sessionId,
        userId: user.id,
        ipAddress: context.ipAddress,
        expiresAt: expiresAt.toISOString(),
      })
    );

    return {
      id: sessionId,
      userId: user.id,
      sessionToken,
      ipAddress: context.ipAddress,
      userAgent: context.userAgent,
      deviceFingerprint: context.deviceFingerprint,
      location: locationInfo,
      isActive: true,
      lastActivity: new Date(),
      createdAt: new Date(),
      expiresAt,
    };
  }

  /**
   * Generate JWT access and refresh tokens
   */
  private async generateTokens(user: User, session: UserSession): Promise<{
    accessToken: string;
    refreshToken: string;
  }> {
    const tokenPayload = {
      userId: user.id,
      email: user.email,
      roles: user.roles,
      sessionId: session.id,
    };

    const accessToken = jwt.sign(tokenPayload, this.JWT_SECRET, {
      expiresIn: this.JWT_EXPIRES_IN,
    });

    const refreshToken = jwt.sign(
      { userId: user.id, sessionId: session.id, type: 'refresh' },
      this.JWT_SECRET,
      { expiresIn: this.REFRESH_TOKEN_EXPIRES_IN }
    );

    // Store refresh token in Redis
    await this.redis.setEx(
      `refresh:${refreshToken}`,
      7 * 24 * 60 * 60, // 7 days
      JSON.stringify({
        userId: user.id,
        sessionId: session.id,
        createdAt: new Date().toISOString(),
      })
    );

    return { accessToken, refreshToken };
  }

  /**
   * Extract token from request headers or cookies
   */
  private extractTokenFromRequest(request: FastifyRequest): string | null {
    // Try Authorization header
    const authHeader = request.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7);
    }

    // Try cookie
    const sessionCookie = request.cookies?.sessionId;
    if (sessionCookie) {
      return sessionCookie;
    }

    return null;
  }

  /**
   * Get valid session from token
   */
  private async getValidSession(sessionId: string): Promise<UserSession | null> {
    const sessionData = await this.redis.get(`session:${sessionId}`);
    if (!sessionData) {
      return null;
    }

    const session = JSON.parse(sessionData);
    if (new Date(session.expiresAt) <= new Date()) {
      await this.redis.del(`session:${sessionId}`);
      return null;
    }

    return session;
  }

  /**
   * Update session activity timestamp
   */
  private async updateSessionActivity(sessionId: string, ipAddress: string): Promise<void> {
    await this.pool.query(
      'UPDATE security.user_sessions SET last_activity = NOW() WHERE id = $1',
      [sessionId]
    );
  }

  /**
   * Revoke session
   */
  private async revokeSession(sessionToken: string): Promise<void> {
    const sessionData = await this.redis.get(`session:${sessionToken}`);
    if (sessionData) {
      const session = JSON.parse(sessionData);
      await this.redis.del(`session:${sessionToken}`);
      await this.pool.query(
        'UPDATE security.user_sessions SET is_active = false WHERE id = $1',
        [session.sessionId]
      );
    }
  }

  /**
   * Generate device fingerprint
   */
  private generateDeviceFingerprint(userAgent: string): string {
    return crypto.createHash('sha256').update(userAgent).digest('hex').substring(0, 16);
  }

  /**
   * Increment failed login attempts
   */
  private async incrementFailedAttempts(userIdOrEmail: string): Promise<void> {
    await this.pool.query(`
      UPDATE users 
      SET failed_login_attempts = failed_login_attempts + 1,
          locked_until = CASE 
            WHEN failed_login_attempts + 1 >= $2 
            THEN NOW() + INTERVAL '${this.LOCKOUT_DURATION} milliseconds'
            ELSE locked_until 
          END,
          updated_at = NOW()
      WHERE id = $1 OR email = $1
    `, [userIdOrEmail, this.MAX_FAILED_ATTEMPTS]);
  }

  /**
   * Reset failed login attempts
   */
  private async resetFailedAttempts(userId: string): Promise<void> {
    await this.pool.query(
      'UPDATE users SET failed_login_attempts = 0, locked_until = NULL, updated_at = NOW() WHERE id = $1',
      [userId]
    );
  }

  /**
   * Update user login information
   */
  private async updateUserLoginInfo(userId: string, ipAddress: string): Promise<void> {
    await this.pool.query(
      'UPDATE users SET last_login = NOW(), last_login_ip = $1, updated_at = NOW() WHERE id = $2',
      [ipAddress, userId]
    );
  }

  /**
   * Log security event
   */
  private async logSecurityEvent(eventType: string, data: any): Promise<void> {
    // This would integrate with the SIEM engine
    // For now, just log to Winston
    this.logger.info('Security event', { eventType, ...data });
  }

  /**
   * Map database row to User interface
   */
  private mapDatabaseRowToUser(row: any): User {
    return {
      id: row.id,
      email: row.email,
      passwordHash: row.password_hash,
      roles: row.roles || [],
      isActive: row.is_active,
      isMfaEnabled: row.is_mfa_enabled,
      lastLogin: row.last_login,
      failedLoginAttempts: row.failed_login_attempts,
      lockedUntil: row.locked_until,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }

  /**
   * Health check for authentication manager
   */
  public async checkHealth(): Promise<string> {
    try {
      await this.pool.query('SELECT 1');
      await this.redis.ping();
      return 'healthy';
    } catch (error) {
      this.logger.error('Auth manager health check failed:', error);
      return 'unhealthy';
    }
  }
}

// Extend Fastify request interface
declare module 'fastify' {
  interface FastifyRequest {
    user?: {
      id: string;
      email: string;
      roles: string[];
      sessionId: string;
    };
  }
}