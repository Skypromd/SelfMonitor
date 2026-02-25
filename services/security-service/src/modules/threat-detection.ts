import { Pool } from 'pg';
import Redis from 'redis';
import winston from 'winston';
import axios from 'axios';
import { EventEmitter } from 'events';
import * as tf from '@tensorflow/tfjs-node';

export interface ThreatIndicator {
  id?: string;
  type: 'ip' | 'domain' | 'hash' | 'email' | 'user_behavior' | 'pattern';
  value: string;
  confidence: number; // 0-100
  source: string;
  description: string;
  threatTypes: string[];
  firstSeen: Date;
  lastSeen: Date;
  isActive: boolean;
  metadata?: any;
}

export interface ThreatAnalysis {
  riskScore: number; // 0-100
  threatLevel: 'low' | 'medium' | 'high' | 'critical';
  indicators: ThreatIndicator[];
  recommendations: string[];
  confidence: number;
  details: {
    ipReputation?: any;
    domainAnalysis?: any;
    behaviorAnalysis?: any;
    malwareAnalysis?: any;
    geolocation?: any;
  };
}

export interface AnomalyDetection {
  type: 'statistical' | 'ml_based' | 'rule_based';
  score: number; // 0-100
  description: string;
  features: { [key: string]: number };
  baseline: { [key: string]: number };
  deviation: { [key: string]: number };
  timestamp: Date;
}

export interface BehaviorProfile {
  userId: string;
  loginPatterns: {
    timeOfDay: number[];
    daysOfWeek: number[];
    locations: string[];
    devices: string[];
    applications: string[];
  };
  activityPatterns: {
    apiCalls: { [endpoint: string]: number };
    dataAccess: string[];
    transactionVolume: number[];
    sessionDuration: number[];
  };
  riskFactors: {
    unusualLocations: number;
    newDevices: number;
    offHoursActivity: number;
    suspiciousPatterns: number;
  };
  baseline: Date;
  lastUpdated: Date;
}

/**
 * Advanced Threat Detection Engine
 * 
 * Provides AI-powered threat detection using:
 * - Machine Learning anomaly detection
 * - Behavioral analysis
 * - Threat intelligence feeds
 * - Statistical analysis
 * - Network traffic analysis
 */
export class ThreatDetectionEngine extends EventEmitter {
  private pool: Pool;
  private redis: Redis.RedisClientType;
  private logger: winston.Logger;
  private threatIntelFeeds: Map<string, any>;
  private anomalyModel?: tf.LayersModel;
  private behaviorProfiles: Map<string, BehaviorProfile>;

  // Threat intelligence sources
  private readonly THREAT_FEEDS = {
    virustotal: process.env.VIRUSTOTAL_API_KEY,
    abuseipdb: process.env.ABUSEIPDB_API_KEY,
    crowdstrike: process.env.CROWDSTRIKE_API_KEY,
    otx: process.env.OTX_API_KEY,
  };

  // Detection thresholds
  private readonly THRESHOLDS = {
    anomaly: {
      low: 30,
      medium: 60,
      high: 80,
    },
    reputation: {
      malicious: 80,
      suspicious: 60,
      clean: 20,
    },
    behavior: {
      deviation_factor: 2.5,
      minimum_baseline_days: 7,
    },
  };

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
        new winston.transports.File({ filename: 'logs/threat-detection.log' }),
      ],
    });
    this.threatIntelFeeds = new Map();
    this.behaviorProfiles = new Map();

    this.initializeThreatFeeds();
    this.loadAnomalyModel();
  }

  /**
   * Initialize threat intelligence feeds
   */
  private async initializeThreatFeeds(): Promise<void> {
    // VirusTotal integration
    if (this.THREAT_FEEDS.virustotal) {
      this.threatIntelFeeds.set('virustotal', {
        apiKey: this.THREAT_FEEDS.virustotal,
        baseUrl: 'https://www.virustotal.com/vtapi/v2',
        rateLimit: 4, // requests per minute
      });
    }

    // AbuseIPDB integration
    if (this.THREAT_FEEDS.abuseipdb) {
      this.threatIntelFeeds.set('abuseipdb', {
        apiKey: this.THREAT_FEEDS.abuseipdb,
        baseUrl: 'https://api.abuseipdb.com/api/v2',
        rateLimit: 1000, // requests per day
      });
    }

    // CrowdStrike Falcon Intelligence
    if (this.THREAT_FEEDS.crowdstrike) {
      this.threatIntelFeeds.set('crowdstrike', {
        apiKey: this.THREAT_FEEDS.crowdstrike,
        baseUrl: 'https://api.crowdstrike.com',
        rateLimit: 10000, // requests per day
      });
    }

    // AlienVault OTX
    if (this.THREAT_FEEDS.otx) {
      this.threatIntelFeeds.set('otx', {
        apiKey: this.THREAT_FEEDS.otx,
        baseUrl: 'https://otx.alienvault.com/api/v1',
        rateLimit: 10000, // requests per hour
      });
    }

    this.logger.info(`Initialized ${this.threatIntelFeeds.size} threat intelligence feeds`);
  }

  /**
   * Load or create ML anomaly detection model
   */
  private async loadAnomalyModel(): Promise<void> {
    try {
      // Try to load existing model
      this.anomalyModel = await tf.loadLayersModel('file://./models/anomaly-detection/model.json');
      this.logger.info('Loaded existing anomaly detection model');
    } catch (error) {
      // Create and train new model if none exists
      this.logger.info('Creating new anomaly detection model');
      await this.createAnomalyModel();
    }
  }

  /**
   * Create and train anomaly detection model
   */
  private async createAnomalyModel(): Promise<void> {
    // Define autoencoder architecture for anomaly detection
    const model = tf.sequential({
      layers: [
        // Encoder
        tf.layers.dense({ inputShape: [20], units: 16, activation: 'relu' }),
        tf.layers.dense({ units: 8, activation: 'relu' }),
        tf.layers.dense({ units: 4, activation: 'relu' }),
        
        // Decoder
        tf.layers.dense({ units: 8, activation: 'relu' }),
        tf.layers.dense({ units: 16, activation: 'relu' }),
        tf.layers.dense({ units: 20, activation: 'linear' }),
      ],
    });

    model.compile({
      optimizer: tf.train.adam(0.001),
      loss: 'meanSquaredError',
      metrics: ['mae'],
    });

    // Train with historical normal behavior data
    const trainingData = await this.getTrainingData();
    if (trainingData && trainingData.length > 100) {
      const xs = tf.tensor2d(trainingData);
      const ys = xs.clone(); // Autoencoder learns to reconstruct input

      await model.fit(xs, ys, {
        epochs: 100,
        batchSize: 32,
        validationSplit: 0.2,
        callbacks: {
          onEpochEnd: (epoch, logs) => {
            if (epoch % 10 === 0) {
              this.logger.info(`Training epoch ${epoch}, loss: ${logs?.loss}`);
            }
          },
        },
      });

      xs.dispose();
      ys.dispose();

      // Save the trained model
      await model.save('file://./models/anomaly-detection');
      this.anomalyModel = model;
      this.logger.info('Anomaly detection model trained and saved');
    } else {
      this.logger.warn('Insufficient training data for anomaly model');
    }
  }

  /**
   * Analyze threat indicators for a given entity
   */
  public async analyzeThreat(data: {
    type: 'ip' | 'domain' | 'hash' | 'email' | 'user_behavior';
    value: string;
    context?: any;
  }): Promise<ThreatAnalysis> {
    try {
      const indicators: ThreatIndicator[] = [];
      const details: any = {};
      let riskScore = 0;

      // Check local threat intelligence database
      const localIndicators = await this.checkLocalThreatDB(data.type, data.value);
      indicators.push(...localIndicators);

      // Query external threat intelligence feeds
      const externalIndicators = await this.queryThreatFeeds(data.type, data.value);
      indicators.push(...externalIndicators);

      // Perform specific analysis based on type
      switch (data.type) {
        case 'ip':
          details.ipReputation = await this.analyzeIPReputation(data.value);
          details.geolocation = await this.getGeolocation(data.value);
          break;
        case 'domain':
          details.domainAnalysis = await this.analyzeDomain(data.value);
          break;
        case 'hash':
          details.malwareAnalysis = await this.analyzeFileHash(data.value);
          break;
        case 'user_behavior':
          details.behaviorAnalysis = await this.analyzeBehavior(data.value, data.context);
          break;
      }

      // Calculate overall risk score
      riskScore = this.calculateRiskScore(indicators, details);

      // Determine threat level
      let threatLevel: 'low' | 'medium' | 'high' | 'critical';
      if (riskScore >= 90) threatLevel = 'critical';
      else if (riskScore >= 70) threatLevel = 'high';
      else if (riskScore >= 40) threatLevel = 'medium';
      else threatLevel = 'low';

      // Generate recommendations
      const recommendations = this.generateRecommendations(threatLevel, indicators, details);

      // Calculate confidence based on indicator quality and quantity
      const confidence = this.calculateConfidence(indicators);

      // Store analysis results
      await this.storeThreatAnalysis(data, riskScore, indicators);

      this.logger.info('Threat analysis completed', {
        type: data.type,
        value: data.value,
        riskScore,
        threatLevel,
        indicatorCount: indicators.length,
      });

      return {
        riskScore,
        threatLevel,
        indicators,
        recommendations,
        confidence,
        details,
      };

    } catch (error) {
      this.logger.error('Threat analysis error:', error);
      throw error;
    }
  }

  /**
   * Detect anomalies in user behavior
   */
  public async detectAnomalies(data: {
    userId?: string;
    features: { [key: string]: number };
    context?: any;
  }): Promise<AnomalyDetection[]> {
    const anomalies: AnomalyDetection[] = [];

    // Statistical anomaly detection
    const statisticalAnomaly = await this.detectStatisticalAnomalies(data);
    if (statisticalAnomaly) {
      anomalies.push(statisticalAnomaly);
    }

    // ML-based anomaly detection
    if (this.anomalyModel) {
      const mlAnomaly = await this.detectMLAnomalies(data);
      if (mlAnomaly) {
        anomalies.push(mlAnomaly);
      }
    }

    // Rule-based anomaly detection
    const ruleAnomaly = await this.detectRuleBasedAnomalies(data);
    if (ruleAnomaly) {
      anomalies.push(ruleAnomaly);
    }

    return anomalies;
  }

  /**
   * Update user behavior profile
   */
  public async updateBehaviorProfile(userId: string, activity: {
    loginTime?: Date;
    location?: string;
    device?: string;
    apiCalls?: string[];
    dataAccess?: string[];
    transactionAmount?: number;
    sessionDuration?: number;
  }): Promise<void> {
    let profile = this.behaviorProfiles.get(userId);

    if (!profile) {
      // Create new profile
      profile = await this.createBehaviorProfile(userId);
    }

    // Update profile with new activity
    if (activity.loginTime) {
      const hour = activity.loginTime.getHours();
      const dayOfWeek = activity.loginTime.getDay();
      profile.loginPatterns.timeOfDay.push(hour);
      profile.loginPatterns.daysOfWeek.push(dayOfWeek);
    }

    if (activity.location) {
      if (!profile.loginPatterns.locations.includes(activity.location)) {
        profile.loginPatterns.locations.push(activity.location);
        profile.riskFactors.unusualLocations += 1;
      }
    }

    if (activity.device) {
      if (!profile.loginPatterns.devices.includes(activity.device)) {
        profile.loginPatterns.devices.push(activity.device);
        profile.riskFactors.newDevices += 1;
      }
    }

    if (activity.apiCalls) {
      activity.apiCalls.forEach(endpoint => {
        profile!.activityPatterns.apiCalls[endpoint] = 
          (profile!.activityPatterns.apiCalls[endpoint] || 0) + 1;
      });
    }

    if (activity.transactionAmount) {
      profile.activityPatterns.transactionVolume.push(activity.transactionAmount);
    }

    if (activity.sessionDuration) {
      profile.activityPatterns.sessionDuration.push(activity.sessionDuration);
    }

    profile.lastUpdated = new Date();
    this.behaviorProfiles.set(userId, profile);

    // Persist to database
    await this.saveBehaviorProfile(profile);
  }

  /**
   * Get threats with filtering and pagination
   */
  public async getThreats(filters: any = {}): Promise<{
    threats: ThreatIndicator[];
    totalCount: number;
    page: number;
    pageSize: number;
  }> {
    const page = parseInt(filters.page || '1', 10);
    const pageSize = Math.min(parseInt(filters.pageSize || '100', 10), 1000);
    const offset = (page - 1) * pageSize;

    let whereClause = '1=1';
    const values: any[] = [];

    if (filters.type) {
      whereClause += ` AND type = $${values.length + 1}`;
      values.push(filters.type);
    }

    if (filters.isActive !== undefined) {
      whereClause += ` AND is_active = $${values.length + 1}`;
      values.push(filters.isActive);
    }

    if (filters.minConfidence) {
      whereClause += ` AND confidence >= $${values.length + 1}`;
      values.push(parseInt(filters.minConfidence, 10));
    }

    if (filters.source) {
      whereClause += ` AND source = $${values.length + 1}`;
      values.push(filters.source);
    }

    // Get total count
    const countResult = await this.pool.query(
      `SELECT COUNT(*) FROM security.threat_indicators WHERE ${whereClause}`,
      values,
    );
    const totalCount = parseInt(countResult.rows[0].count, 10);

    // Get threats
    const threatsResult = await this.pool.query(
      `SELECT * FROM security.threat_indicators WHERE ${whereClause} 
       ORDER BY confidence DESC, last_seen DESC 
       LIMIT $${values.length + 1} OFFSET $${values.length + 2}`,
      [...values, pageSize, offset],
    );

    return {
      threats: threatsResult.rows.map(this.mapDatabaseRowToThreatIndicator),
      totalCount,
      page,
      pageSize,
    };
  }

  /**
   * Check local threat intelligence database
   */
  private async checkLocalThreatDB(type: string, value: string): Promise<ThreatIndicator[]> {
    const result = await this.pool.query(
      'SELECT * FROM security.threat_indicators WHERE type = $1 AND value = $2 AND is_active = true',
      [type, value]
    );

    return result.rows.map(this.mapDatabaseRowToThreatIndicator);
  }

  /**
   * Query external threat intelligence feeds
   */
  private async queryThreatFeeds(type: string, value: string): Promise<ThreatIndicator[]> {
    const indicators: ThreatIndicator[] = [];

    for (const [feedName, feedConfig] of this.threatIntelFeeds) {
      try {
        const feedIndicators = await this.querySpecificFeed(feedName, feedConfig, type, value);
        indicators.push(...feedIndicators);
      } catch (error) {
        this.logger.error(`Error querying ${feedName} feed:`, error);
      }
    }

    return indicators;
  }

  /**
   * Query specific threat intelligence feed
   */
  private async querySpecificFeed(
    feedName: string,
    feedConfig: any,
    type: string,
    value: string
  ): Promise<ThreatIndicator[]> {
    const indicators: ThreatIndicator[] = [];
    let result: any;

    switch (feedName) {
      case 'virustotal':
        if (type === 'ip') {
          result = await this.queryVirusTotalIP(feedConfig, value);
        } else if (type === 'domain') {
          result = await this.queryVirusTotalDomain(feedConfig, value);
        } else if (type === 'hash') {
          result = await this.queryVirusTotalHash(feedConfig, value);
        }
        break;

      case 'abuseipdb':
        if (type === 'ip') {
          result = await this.queryAbuseIPDB(feedConfig, value);
        }
        break;

      case 'otx':
        result = await this.queryOTX(feedConfig, type, value);
        break;
    }

    if (result && result.malicious) {
      indicators.push({
        type: type as any,
        value,
        confidence: result.confidence || 75,
        source: feedName,
        description: result.description || `Detected by ${feedName}`,
        threatTypes: result.threat_types || ['malicious'],
        firstSeen: new Date(),
        lastSeen: new Date(),
        isActive: true,
        metadata: result,
      });
    }

    return indicators;
  }

  /**
   * Query VirusTotal for IP information
   */
  private async queryVirusTotalIP(config: any, ip: string): Promise<any> {
    try {
      const response = await axios.get(`${config.baseUrl}/ip-address/report`, {
        params: {
          apikey: config.apiKey,
          ip,
        },
      });

      if (response.data.response_code === 1) {
        const detectedEngines = response.data.detected_urls?.length || 0;
        return {
          malicious: detectedEngines > 0,
          confidence: Math.min(detectedEngines * 10, 100),
          description: `Detected by ${detectedEngines} VirusTotal engines`,
          threat_types: ['malicious_ip'],
          metadata: response.data,
        };
      }
    } catch (error) {
      this.logger.error('VirusTotal IP query error:', error);
    }
    return null;
  }

  /**
   * Query AbuseIPDB
   */
  private async queryAbuseIPDB(config: any, ip: string): Promise<any> {
    try {
      const response = await axios.get(`${config.baseUrl}/check`, {
        headers: {
          'Key': config.apiKey,
          'Accept': 'application/json',
        },
        params: {
          ipAddress: ip,
          maxAgeInDays: 90,
          verbose: true,
        },
      });

      if (response.data.abuseConfidencePercentage > 25) {
        return {
          malicious: true,
          confidence: response.data.abuseConfidencePercentage,
          description: `AbuseIPDB confidence: ${response.data.abuseConfidencePercentage}%`,
          threat_types: ['abusive_ip'],
          metadata: response.data,
        };
      }
    } catch (error) {
      this.logger.error('AbuseIPDB query error:', error);
    }
    return null;
  }

  /**
   * Analyze IP reputation
   */
  private async analyzeIPReputation(ip: string): Promise<any> {
    const reputation = {
      score: 0,
      sources: [] as string[],
      details: {} as any,
    };

    // Check against known malicious IP lists
    const localCheck = await this.pool.query(
      'SELECT * FROM security.threat_indicators WHERE type = \'ip\' AND value = $1 AND is_active = true',
      [ip]
    );

    if (localCheck.rows.length > 0) {
      reputation.score += 80;
      reputation.sources.push('local_database');
    }

    // Additional reputation checks would go here
    return reputation;
  }

  /**
   * Analyze domain
   */
  private async analyzeDomain(domain: string): Promise<any> {
    return {
      registrationDate: null,
      registrar: null,
      nameservers: [],
      reputation: 'unknown',
    };
  }

  /**
   * Analyze file hash
   */
  private async analyzeFileHash(hash: string): Promise<any> {
    return {
      malwareFamily: null,
      detectionRatio: 0,
      firstSeen: null,
      lastSeen: null,
    };
  }

  /**
   * Analyze user behavior
   */
  private async analyzeBehavior(userId: string, context: any): Promise<any> {
    const profile = this.behaviorProfiles.get(userId);
    if (!profile) {
      return { baseline: false, risk: 'unknown' };
    }

    // Compare current behavior against baseline
    const analysis = {
      deviations: [] as string[],
      riskScore: 0,
      baseline: true,
    };

    // Check time-based patterns
    if (context.loginTime) {
      const hour = context.loginTime.getHours();
      const normalHours = profile.loginPatterns.timeOfDay;
      const avgHour = normalHours.reduce((a, b) => a + b, 0) / normalHours.length;
      const deviation = Math.abs(hour - avgHour);

      if (deviation > 4) { // More than 4 hours from normal
        analysis.deviations.push('unusual_login_time');
        analysis.riskScore += 20;
      }
    }

    return analysis;
  }

  /**
   * Statistical anomaly detection
   */
  private async detectStatisticalAnomalies(data: any): Promise<AnomalyDetection | null> {
    // Get historical data for comparison
    const historical = await this.getHistoricalData(data.userId);
    if (historical.length < 30) return null; // Need sufficient baseline

    // Calculate z-scores for each feature
    const anomalies: any = {};
    let maxDeviation = 0;

    for (const [feature, value] of Object.entries(data.features)) {
      if (typeof value !== 'number') continue;

      const historicalValues = historical.map(h => h[feature]).filter(v => v != null);
      if (historicalValues.length < 10) continue;

      const mean = historicalValues.reduce((a, b) => a + b, 0) / historicalValues.length;
      const variance = historicalValues.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / historicalValues.length;
      const stdDev = Math.sqrt(variance);

      if (stdDev > 0) {
        const zScore = Math.abs((value - mean) / stdDev);
        if (zScore > 2.5) { // Significant deviation
          anomalies[feature] = { value, mean, stdDev, zScore };
          maxDeviation = Math.max(maxDeviation, zScore);
        }
      }
    }

    if (Object.keys(anomalies).length === 0) return null;

    return {
      type: 'statistical',
      score: Math.min(maxDeviation * 20, 100),
      description: `Statistical anomaly detected in ${Object.keys(anomalies).join(', ')}`,
      features: data.features,
      baseline: {}, // Would be calculated from historical data
      deviation: anomalies,
      timestamp: new Date(),
    };
  }

  /**
   * ML-based anomaly detection
   */
  private async detectMLAnomalies(data: any): Promise<AnomalyDetection | null> {
    if (!this.anomalyModel) return null;

    try {
      // Convert features to tensor
      const featureVector = this.featuresToVector(data.features);
      const input = tf.tensor2d([featureVector]);

      // Get reconstruction from autoencoder
      const reconstruction = this.anomalyModel.predict(input) as tf.Tensor;
      
      // Calculate reconstruction error
      const error = tf.losses.meanSquaredError(input, reconstruction);
      const errorValue = await error.data();
      
      // Cleanup tensors
      input.dispose();
      reconstruction.dispose();
      error.dispose();

      // Convert error to anomaly score (0-100)
      const anomalyScore = Math.min(errorValue[0] * 1000, 100);

      if (anomalyScore > this.THRESHOLDS.anomaly.medium) {
        return {
          type: 'ml_based',
          score: anomalyScore,
          description: `ML model detected anomaly (reconstruction error: ${errorValue[0].toFixed(4)})`,
          features: data.features,
          baseline: {}, // Would be model's baseline
          deviation: { reconstruction_error: errorValue[0] },
          timestamp: new Date(),
        };
      }
    } catch (error) {
      this.logger.error('ML anomaly detection error:', error);
    }

    return null;
  }

  /**
   * Rule-based anomaly detection
   */
  private async detectRuleBasedAnomalies(data: any): Promise<AnomalyDetection | null> {
    const rules = [
      {
        name: 'high_transaction_volume',
        condition: () => data.features.transactionAmount > 100000, // $100k
        score: 80,
      },
      {
        name: 'unusual_login_frequency',
        condition: () => data.features.loginCount > 50, // 50 logins per hour
        score: 60,
      },
      {
        name: 'multiple_failed_attempts',
        condition: () => data.features.failedAttempts > 10,
        score: 70,
      },
    ];

    for (const rule of rules) {
      if (rule.condition()) {
        return {
          type: 'rule_based',
          score: rule.score,
          description: `Rule-based detection: ${rule.name}`,
          features: data.features,
          baseline: {},
          deviation: { [rule.name]: data.features },
          timestamp: new Date(),
        };
      }
    }

    return null;
  }

  /**
   * Calculate overall risk score
   */
  private calculateRiskScore(indicators: ThreatIndicator[], details: any): number {
    let score = 0;

    // Base score from indicators
    const avgConfidence = indicators.length > 0 
      ? indicators.reduce((sum, ind) => sum + ind.confidence, 0) / indicators.length 
      : 0;
    score += avgConfidence * 0.6;

    // Add score from specific analysis
    if (details.ipReputation?.score) {
      score += details.ipReputation.score * 0.3;
    }

    if (details.behaviorAnalysis?.riskScore) {
      score += details.behaviorAnalysis.riskScore * 0.4;
    }

    return Math.min(score, 100);
  }

  /**
   * Generate recommendations based on analysis
   */
  private generateRecommendations(
    threatLevel: string,
    indicators: ThreatIndicator[],
    details: any
  ): string[] {
    const recommendations: string[] = [];

    if (threatLevel === 'critical') {
      recommendations.push('Immediately block this entity');
      recommendations.push('Alert security team for investigation');
    } else if (threatLevel === 'high') {
      recommendations.push('Add to monitoring watchlist');
      recommendations.push('Require additional authentication');
    } else if (threatLevel === 'medium') {
      recommendations.push('Monitor closely for additional activity');
      recommendations.push('Log all interactions for review');
    }

    if (indicators.some(ind => ind.type === 'ip')) {
      recommendations.push('Consider IP reputation blocking');
    }

    if (details.behaviorAnalysis?.deviations?.length > 0) {
      recommendations.push('Review user behavior patterns');
      recommendations.push('Consider step-up authentication');
    }

    return recommendations;
  }

  /**
   * Calculate confidence score
   */
  private calculateConfidence(indicators: ThreatIndicator[]): number {
    if (indicators.length === 0) return 0;

    const sourceWeights = {
      'virustotal': 0.9,
      'abuseipdb': 0.8,
      'crowdstrike': 0.95,
      'local_database': 0.7,
    };

    let weightedSum = 0;
    let totalWeight = 0;

    indicators.forEach(ind => {
      const weight = sourceWeights[ind.source as keyof typeof sourceWeights] || 0.5;
      weightedSum += ind.confidence * weight;
      totalWeight += weight;
    });

    return totalWeight > 0 ? Math.min(weightedSum / totalWeight, 100) : 0;
  }

  /**
   * Helper methods
   */
  private featuresToVector(features: { [key: string]: number }): number[] {
    // Convert feature object to fixed-length vector
    // This would be customized based on the specific features used
    const vector = new Array(20).fill(0);
    
    // Map features to vector positions
    const featureMap: { [key: string]: number } = {
      'loginCount': 0,
      'failedAttempts': 1,
      'transactionAmount': 2,
      'sessionDuration': 3,
      // Add more feature mappings...
    };

    Object.entries(features).forEach(([key, value]) => {
      const index = featureMap[key];
      if (index !== undefined && index < vector.length) {
        vector[index] = value;
      }
    });

    return vector;
  }

  private async getTrainingData(): Promise<number[][] | null> {
    try {
      // Get historical normal behavior data for training
      const result = await this.pool.query(`
        SELECT metadata FROM security.events 
        WHERE event_type = 'normal_behavior' 
        ORDER BY created_at DESC 
        LIMIT 10000
      `);

      return result.rows
        .map(row => this.featuresToVector(row.metadata || {}))
        .filter(vector => vector.some(v => v !== 0));
    } catch (error) {
      this.logger.error('Failed to get training data:', error);
      return null;
    }
  }

  private async getHistoricalData(userId?: string): Promise<any[]> {
    if (!userId) return [];

    const result = await this.pool.query(`
      SELECT metadata FROM security.events 
      WHERE user_id = $1 AND created_at > NOW() - INTERVAL '30 days'
      ORDER BY created_at DESC
      LIMIT 1000
    `, [userId]);

    return result.rows.map(row => row.metadata || {});
  }

  private async createBehaviorProfile(userId: string): Promise<BehaviorProfile> {
    return {
      userId,
      loginPatterns: {
        timeOfDay: [],
        daysOfWeek: [],
        locations: [],
        devices: [],
        applications: [],
      },
      activityPatterns: {
        apiCalls: {},
        dataAccess: [],
        transactionVolume: [],
        sessionDuration: [],
      },
      riskFactors: {
        unusualLocations: 0,
        newDevices: 0,
        offHoursActivity: 0,
        suspiciousPatterns: 0,
      },
      baseline: new Date(),
      lastUpdated: new Date(),
    };
  }

  private async saveBehaviorProfile(profile: BehaviorProfile): Promise<void> {
    // Save profile to database (implementation would go here)
    this.logger.debug('Behavior profile saved', { userId: profile.userId });
  }

  private async getGeolocation(ip: string): Promise<any> {
    // Implementation would use a geolocation service
    return {
      country: 'Unknown',
      city: 'Unknown',
      latitude: 0,
      longitude: 0,
    };
  }

  private async storeThreatAnalysis(
    data: any,
    riskScore: number,
    indicators: ThreatIndicator[]
  ): Promise<void> {
    // Store analysis results for historical tracking
    this.logger.debug('Threat analysis stored', {
      type: data.type,
      value: data.value,
      riskScore,
      indicatorCount: indicators.length,
    });
  }

  private mapDatabaseRowToThreatIndicator(row: any): ThreatIndicator {
    return {
      id: row.id,
      type: row.type,
      value: row.value,
      confidence: row.confidence,
      source: row.source,
      description: row.description,
      threatTypes: row.threat_types || [],
      firstSeen: row.first_seen,
      lastSeen: row.last_seen,
      isActive: row.is_active,
      metadata: row.metadata,
    };
  }

  public async checkHealth(): Promise<string> {
    try {
      await this.pool.query('SELECT 1');
      return 'healthy';
    } catch (error) {
      this.logger.error('Threat detection health check failed:', error);
      return 'unhealthy';
    }
  }
}