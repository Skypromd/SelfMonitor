import { Pool } from 'pg';
import Redis from 'redis';
import winston from 'winston';
import axios from 'axios';
import { EventEmitter } from 'events';

export interface SecurityEvent {
  id?: string;
  userId?: string;
  sessionId?: string;
  eventType: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  ipAddress: string;
  userAgent: string;
  location?: any;
  deviceInfo?: any;
  timestamp?: Date;
  metadata?: any;
}

export interface SecurityMetrics {
  totalEvents: number;
  eventsLast24h: number;
  eventsLast7d: number;
  eventsByType: { [key: string]: number };
  eventsBySeverity: { [key: string]: number };
  topIPAddresses: Array<{ ip: string; count: number }>;
  topUserAgents: Array<{ userAgent: string; count: number }>;
  averageResponseTime: number;
  threatLevel: 'low' | 'medium' | 'high' | 'critical';
}

export interface SecurityDashboard {
  overview: {
    activeIncidents: number;
    resolvedIncidents: number;
    criticalAlerts: number;
    systemHealth: string;
  };
  realTimeMetrics: SecurityMetrics;
  recentEvents: SecurityEvent[];
  topThreats: Array<{
    type: string;
    count: number;
    trend: 'increasing' | 'decreasing' | 'stable';
  }>;
  complianceStatus: {
    soc2: number;
    iso27001: number;
    gdpr: number;
    overall: number;
  };
}

/**
 * SIEM (Security Information and Event Management) Engine
 * 
 * Provides centralized security event logging, correlation, and analysis
 * with real-time threat detection and compliance monitoring.
 */
export class SIEMEngine extends EventEmitter {
  private pool: Pool;
  private redis: Redis.RedisClientType;
  private logger: winston.Logger;
  private elasticsearchClient?: any;
  private splunkClient?: any;

  constructor() {
    super();
    this.pool = new Pool({
      connectionString: process.env.SECURITY_DATABASE_URL || 'postgresql://localhost:5432/security',
    });
    this.redis = Redis.createClient({
      url: process.env.SECURITY_REDIS_URL || 'redis://localhost:6379/3',
    });
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json(),
      ),
      transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'logs/siem.log' }),
      ],
    });

    this.initializeExternalSIEMs();
  }

  /**
   * Initialize connections to external SIEM platforms
   */
  private async initializeExternalSIEMs(): Promise<void> {
    // Elasticsearch integration
    if (process.env.ELASTICSEARCH_URL) {
      try {
        const { Client } = await import('@elastic/elasticsearch');
        this.elasticsearchClient = new Client({
          node: process.env.ELASTICSEARCH_URL,
          auth: {
            apiKey: process.env.ELASTICSEARCH_API_KEY || '',
          },
        });
        this.logger.info('Elasticsearch SIEM integration initialized');
      } catch (error) {
        this.logger.error('Failed to initialize Elasticsearch:', error);
      }
    }

    // Splunk integration
    if (process.env.SPLUNK_URL) {
      try {
        const splunkLogging = await import('splunk-logging');
        this.splunkClient = new splunkLogging.Logger({
          token: process.env.SPLUNK_TOKEN || '',
          url: process.env.SPLUNK_URL,
          source: 'selfmonitor-security',
          sourcetype: 'json',
        });
        this.logger.info('Splunk SIEM integration initialized');
      } catch (error) {
        this.logger.error('Failed to initialize Splunk:', error);
      }
    }
  }

  /**
   * Log a security event to all configured SIEM systems
   */
  public async logSecurityEvent(event: SecurityEvent): Promise<string> {
    try {
      const eventId = await this.storeEvent(event);
      await this.correlateEvent(event);
      await this.sendToExternalSIEMs(event);
      await this.updateMetrics(event);
      await this.checkAlertThresholds(event);

      // Emit event for real-time processing
      this.emit('securityEvent', event);

      this.logger.info('Security event logged', { eventId, eventType: event.eventType });
      return eventId;
    } catch (error) {
      this.logger.error('Failed to log security event:', error);
      throw error;
    }
  }

  /**
   * Store security event in database
   */
  private async storeEvent(event: SecurityEvent): Promise<string> {
    const query = `
      INSERT INTO security.events (
        user_id, session_id, event_type, severity, description,
        ip_address, user_agent, location, device_info, metadata
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
      RETURNING id
    `;

    const values = [
      event.userId || null,
      event.sessionId || null,
      event.eventType,
      event.severity,
      event.description,
      event.ipAddress,
      event.userAgent,
      JSON.stringify(event.location || {}),
      JSON.stringify(event.deviceInfo || {}),
      JSON.stringify(event.metadata || {}),
    ];

    const result = await this.pool.query(query, values);
    return result.rows[0].id;
  }

  /**
   * Correlate events to detect patterns and potential attacks
   */
  private async correlateEvent(event: SecurityEvent): Promise<void> {
    // Check for multiple failed login attempts from same IP
    if (event.eventType === 'login_failed') {
      const failedAttempts = await this.getRecentEventCount(
        'login_failed',
        { ipAddress: event.ipAddress },
        5 * 60 * 1000, // 5 minutes
      );

      if (failedAttempts >= 5) {
        await this.logSecurityEvent({
          eventType: 'brute_force_attack',
          severity: 'high',
          description: `Multiple failed login attempts from IP ${event.ipAddress}`,
          ipAddress: event.ipAddress,
          userAgent: event.userAgent,
          metadata: { originalEvent: event, attemptCount: failedAttempts },
        });
      }
    }

    // Check for suspicious user behavior patterns
    if (event.userId) {
      await this.analyzeBehaviorPatterns(event);
    }

    // Check for known threat indicators
    await this.checkThreatIndicators(event);
  }

  /**
   * Analyze user behavior patterns for anomalies
   */
  private async analyzeBehaviorPatterns(event: SecurityEvent): Promise<void> {
    const userEvents = await this.pool.query(`
      SELECT event_type, ip_address, user_agent, location, created_at
      FROM security.events
      WHERE user_id = $1 AND created_at > NOW() - INTERVAL '24 hours'
      ORDER BY created_at DESC
      LIMIT 100
    `, [event.userId]);

    const events = userEvents.rows;
    
    // Detect login from new location
    if (event.eventType === 'login_success') {
      const recentLocations = events
        .filter(e => e.event_type === 'login_success')
        .map(e => e.location)
        .filter(Boolean);

      if (recentLocations.length > 0) {
        const currentLocation = event.location;
        const isNewLocation = !recentLocations.some(loc => 
          this.isLocationSimilar(loc, currentLocation)
        );

        if (isNewLocation) {
          await this.logSecurityEvent({
            eventType: 'login_new_location',
            severity: 'medium',
            description: `User logged in from new location: ${JSON.stringify(currentLocation)}`,
            ipAddress: event.ipAddress,
            userAgent: event.userAgent,
            userId: event.userId,
            metadata: { originalEvent: event },
          });
        }
      }
    }

    // Detect unusual activity patterns
    const eventTypes = events.reduce((acc, e) => {
      acc[e.event_type] = (acc[e.event_type] || 0) + 1;
      return acc;
    }, {} as { [key: string]: number });

    const totalEvents = events.length;
    if (totalEvents > 50) { // High activity threshold
      await this.logSecurityEvent({
        eventType: 'unusual_activity_volume',
        severity: 'medium',
        description: `User has ${totalEvents} events in the last 24 hours`,
        ipAddress: event.ipAddress,
        userAgent: event.userAgent,
        userId: event.userId,
        metadata: { eventCounts: eventTypes, originalEvent: event },
      });
    }
  }

  /**
   * Check event against threat indicators database
   */
  private async checkThreatIndicators(event: SecurityEvent): Promise<void> {
    const threats = await this.pool.query(`
      SELECT * FROM security.threat_indicators
      WHERE is_active = true
      AND (
        (type = 'ip' AND value = $1)
        OR (type = 'user_behavior' AND $2 ~ value)
      )
    `, [event.ipAddress, event.eventType]);

    for (const threat of threats.rows) {
      await this.logSecurityEvent({
        eventType: 'threat_indicator_match',
        severity: threat.confidence > 80 ? 'high' : 'medium',
        description: `Event matches threat indicator: ${threat.description}`,
        ipAddress: event.ipAddress,
        userAgent: event.userAgent,
        userId: event.userId,
        metadata: { 
          threatIndicator: threat,
          originalEvent: event,
        },
      });

      // Update threat indicator last seen time
      await this.pool.query(`
        UPDATE security.threat_indicators
        SET last_seen = NOW(), updated_at = NOW()
        WHERE id = $1
      `, [threat.id]);
    }
  }

  /**
   * Send events to external SIEM platforms
   */
  private async sendToExternalSIEMs(event: SecurityEvent): Promise<void> {
    const siemEvent = {
      timestamp: new Date().toISOString(),
      source: 'selfmonitor-security-service',
      ...event,
    };

    // Send to Elasticsearch
    if (this.elasticsearchClient) {
      try {
        await this.elasticsearchClient.index({
          index: `selfmonitor-security-${new Date().toISOString().split('T')[0]}`,
          body: siemEvent,
        });
      } catch (error) {
        this.logger.error('Failed to send event to Elasticsearch:', error);
      }
    }

    // Send to Splunk
    if (this.splunkClient) {
      try {
        this.splunkClient.send(siemEvent);
      } catch (error) {
        this.logger.error('Failed to send event to Splunk:', error);
      }
    }
  }

  /**
   * Update real-time metrics
   */
  private async updateMetrics(event: SecurityEvent): Promise<void> {
    const today = new Date().toISOString().split('T')[0];
    const hour = new Date().getHours();

    // Update daily counters
    await this.redis.incr(`security:metrics:events:${today}`);
    await this.redis.incr(`security:metrics:events:${today}:${hour}`);
    await this.redis.incr(`security:metrics:type:${event.eventType}:${today}`);
    await this.redis.incr(`security:metrics:severity:${event.severity}:${today}`);
    await this.redis.incr(`security:metrics:ip:${event.ipAddress}:${today}`);

    // Set expiration for metrics (30 days)
    await this.redis.expire(`security:metrics:events:${today}`, 30 * 24 * 60 * 60);
    await this.redis.expire(`security:metrics:type:${event.eventType}:${today}`, 30 * 24 * 60 * 60);
    await this.redis.expire(`security:metrics:severity:${event.severity}:${today}`, 30 * 24 * 60 * 60);
    await this.redis.expire(`security:metrics:ip:${event.ipAddress}:${today}`, 30 * 24 * 60 * 60);
  }

  /**
   * Check if event triggers any alert thresholds
   */
  private async checkAlertThresholds(event: SecurityEvent): Promise<void> {
    const alertRules = [
      {
        name: 'high_severity_events',
        condition: () => event.severity === 'critical',
        action: () => this.sendAlert('Critical security event detected', event),
      },
      {
        name: 'mass_login_failures',
        condition: async () => {
          const failureCount = await this.getRecentEventCount('login_failed', {}, 60 * 1000);
          return failureCount >= 20;
        },
        action: () => this.sendAlert('Mass login failure attack detected', event),
      },
      {
        name: 'rapid_events_single_ip',
        condition: async () => {
          const ipEventCount = await this.getRecentEventCount(null, { ipAddress: event.ipAddress }, 60 * 1000);
          return ipEventCount >= 100;
        },
        action: () => this.sendAlert('Rapid event generation from single IP', event),
      },
    ];

    for (const rule of alertRules) {
      try {
        if (await rule.condition()) {
          await rule.action();
        }
      } catch (error) {
        this.logger.error(`Failed to process alert rule ${rule.name}:`, error);
      }
    }
  }

  /**
   * Send security alert
   */
  private async sendAlert(message: string, event: SecurityEvent): Promise<void> {
    // Send to monitoring system
    this.emit('securityAlert', { message, event, severity: event.severity });

    // Send to external alerting systems
    if (process.env.SLACK_WEBHOOK_URL) {
      try {
        await axios.post(process.env.SLACK_WEBHOOK_URL, {
          text: `🚨 Security Alert: ${message}`,
          attachments: [{
            color: event.severity === 'critical' ? 'danger' : 'warning',
            fields: [
              { title: 'Event Type', value: event.eventType, short: true },
              { title: 'Severity', value: event.severity, short: true },
              { title: 'IP Address', value: event.ipAddress, short: true },
              { title: 'Description', value: event.description, short: false },
            ],
            ts: Math.floor(Date.now() / 1000),
          }],
        });
      } catch (error) {
        this.logger.error('Failed to send Slack alert:', error);
      }
    }
  }

  /**
   * Get count of recent events matching criteria
   */
  private async getRecentEventCount(
    eventType: string | null,
    filters: { [key: string]: any },
    timeWindowMs: number,
  ): Promise<number> {
    let whereClause = 'created_at > NOW() - INTERVAL $1';
    const values: any[] = [`${timeWindowMs} milliseconds`];

    if (eventType) {
      whereClause += ' AND event_type = $2';
      values.push(eventType);
    }

    if (filters.ipAddress) {
      whereClause += ` AND ip_address = $${values.length + 1}`;
      values.push(filters.ipAddress);
    }

    if (filters.userId) {
      whereClause += ` AND user_id = $${values.length + 1}`;
      values.push(filters.userId);
    }

    const result = await this.pool.query(
      `SELECT COUNT(*) FROM security.events WHERE ${whereClause}`,
      values,
    );

    return parseInt(result.rows[0].count, 10);
  }

  /**
   * Get security events with pagination and filtering
   */
  public async getSecurityEvents(filters: any = {}): Promise<{
    events: SecurityEvent[];
    totalCount: number;
    page: number;
    pageSize: number;
  }> {
    const page = parseInt(filters.page || '1', 10);
    const pageSize = Math.min(parseInt(filters.pageSize || '100', 10), 1000);
    const offset = (page - 1) * pageSize;

    let whereClause = '1=1';
    const values: any[] = [];

    if (filters.eventType) {
      whereClause += ` AND event_type = $${values.length + 1}`;
      values.push(filters.eventType);
    }

    if (filters.severity) {
      whereClause += ` AND severity = $${values.length + 1}`;
      values.push(filters.severity);
    }

    if (filters.userId) {
      whereClause += ` AND user_id = $${values.length + 1}`;
      values.push(filters.userId);
    }

    if (filters.startDate) {
      whereClause += ` AND created_at >= $${values.length + 1}`;
      values.push(filters.startDate);
    }

    if (filters.endDate) {
      whereClause += ` AND created_at <= $${values.length + 1}`;
      values.push(filters.endDate);
    }

    // Get total count
    const countResult = await this.pool.query(
      `SELECT COUNT(*) FROM security.events WHERE ${whereClause}`,
      values,
    );
    const totalCount = parseInt(countResult.rows[0].count, 10);

    // Get events
    const eventsResult = await this.pool.query(
      `SELECT * FROM security.events WHERE ${whereClause} 
       ORDER BY created_at DESC 
       LIMIT $${values.length + 1} OFFSET $${values.length + 2}`,
      [...values, pageSize, offset],
    );

    return {
      events: eventsResult.rows.map(this.mapDatabaseRowToEvent),
      totalCount,
      page,
      pageSize,
    };
  }

  /**
   * Get security metrics for dashboard
   */
  public async getSecurityMetrics(timeRange: any = {}): Promise<SecurityMetrics> {
    const now = new Date();
    const last24h = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    const last7d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

    // Get event counts
    const totalEventsResult = await this.pool.query(
      'SELECT COUNT(*) FROM security.events',
    );

    const events24hResult = await this.pool.query(
      'SELECT COUNT(*) FROM security.events WHERE created_at > $1',
      [last24h],
    );

    const events7dResult = await this.pool.query(
      'SELECT COUNT(*) FROM security.events WHERE created_at > $1',
      [last7d],
    );

    // Get events by type
    const eventsByTypeResult = await this.pool.query(`
      SELECT event_type, COUNT(*) as count
      FROM security.events
      WHERE created_at > $1
      GROUP BY event_type
      ORDER BY count DESC
      LIMIT 10
    `, [last24h]);

    // Get events by severity
    const eventsBySeverityResult = await this.pool.query(`
      SELECT severity, COUNT(*) as count
      FROM security.events
      WHERE created_at > $1
      GROUP BY severity
      ORDER BY count DESC
    `, [last24h]);

    // Get top IP addresses
    const topIPsResult = await this.pool.query(`
      SELECT ip_address, COUNT(*) as count
      FROM security.events
      WHERE created_at > $1
      GROUP BY ip_address
      ORDER BY count DESC
      LIMIT 10
    `, [last24h]);

    // Get top user agents
    const topUserAgentsResult = await this.pool.query(`
      SELECT user_agent, COUNT(*) as count
      FROM security.events
      WHERE created_at > $1 AND user_agent IS NOT NULL
      GROUP BY user_agent
      ORDER BY count DESC
      LIMIT 10
    `, [last24h]);

    // Calculate threat level based on recent critical events
    const criticalEventsResult = await this.pool.query(
      'SELECT COUNT(*) FROM security.events WHERE severity = \'critical\' AND created_at > $1',
      [last24h],
    );

    const criticalEventsCount = parseInt(criticalEventsResult.rows[0].count, 10);
    let threatLevel: 'low' | 'medium' | 'high' | 'critical';

    if (criticalEventsCount > 10) {
      threatLevel = 'critical';
    } else if (criticalEventsCount > 5) {
      threatLevel = 'high';
    } else if (criticalEventsCount > 1) {
      threatLevel = 'medium';
    } else {
      threatLevel = 'low';
    }

    return {
      totalEvents: parseInt(totalEventsResult.rows[0].count, 10),
      eventsLast24h: parseInt(events24hResult.rows[0].count, 10),
      eventsLast7d: parseInt(events7dResult.rows[0].count, 10),
      eventsByType: eventsByTypeResult.rows.reduce((acc, row) => {
        acc[row.event_type] = parseInt(row.count, 10);
        return acc;
      }, {}),
      eventsBySeverity: eventsBySeverityResult.rows.reduce((acc, row) => {
        acc[row.severity] = parseInt(row.count, 10);
        return acc;
      }, {}),
      topIPAddresses: topIPsResult.rows.map(row => ({
        ip: row.ip_address,
        count: parseInt(row.count, 10),
      })),
      topUserAgents: topUserAgentsResult.rows.map(row => ({
        userAgent: row.user_agent,
        count: parseInt(row.count, 10),
      })),
      averageResponseTime: 0, // To be implemented with performance monitoring
      threatLevel,
    };
  }

  /**
   * Get security dashboard data
   */
  public async getSecurityDashboard(): Promise<SecurityDashboard> {
    const metrics = await this.getSecurityMetrics();
    const recentEvents = await this.getSecurityEvents({ pageSize: 20 });

    // Get threat intelligence summary
    const threatsResult = await this.pool.query(`
      SELECT type, COUNT(*) as count
      FROM security.threat_indicators
      WHERE is_active = true
      GROUP BY type
      ORDER BY count DESC
    `);

    // Mock compliance status (to be implemented with actual compliance checks)
    const complianceStatus = {
      soc2: 85,
      iso27001: 78,
      gdpr: 92,
      overall: 85,
    };

    return {
      overview: {
        activeIncidents: metrics.eventsBySeverity.critical || 0,
        resolvedIncidents: 0, // To be implemented with incident tracking
        criticalAlerts: (metrics.eventsBySeverity.critical || 0) + (metrics.eventsBySeverity.high || 0),
        systemHealth: metrics.threatLevel === 'low' ? 'healthy' : 'warning',
      },
      realTimeMetrics: metrics,
      recentEvents: recentEvents.events,
      topThreats: threatsResult.rows.map(row => ({
        type: row.type,
        count: parseInt(row.count, 10),
        trend: 'stable' as const, // To be implemented with trend analysis
      })),
      complianceStatus,
    };
  }

  /**
   * Health check for SIEM engine
   */
  public async checkHealth(): Promise<string> {
    try {
      await this.pool.query('SELECT 1');
      return 'healthy';
    } catch (error) {
      this.logger.error('SIEM health check failed:', error);
      return 'unhealthy';
    }
  }

  /**
   * Helper method to check if two locations are similar
   */
  private isLocationSimilar(loc1: any, loc2: any): boolean {
    if (!loc1 || !loc2) return false;
    
    // Simple distance calculation (can be improved with more sophisticated geolocation)
    const city1 = loc1.city?.toLowerCase();
    const city2 = loc2.city?.toLowerCase();
    const country1 = loc1.country?.toLowerCase();
    const country2 = loc2.country?.toLowerCase();

    return city1 === city2 && country1 === country2;
  }

  /**
   * Map database row to SecurityEvent interface
   */
  private mapDatabaseRowToEvent(row: any): SecurityEvent {
    return {
      id: row.id,
      userId: row.user_id,
      sessionId: row.session_id,
      eventType: row.event_type,
      severity: row.severity,
      description: row.description,
      ipAddress: row.ip_address,
      userAgent: row.user_agent,
      location: row.location,
      deviceInfo: row.device_info,
      timestamp: row.created_at,
      metadata: row.metadata,
    };
  }
}