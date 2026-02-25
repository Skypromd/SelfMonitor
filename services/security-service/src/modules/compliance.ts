import { Pool } from 'pg';
import Redis from 'redis';
import winston from 'winston';
import axios from 'axios';
import { EventEmitter } from 'events';
import * as fs from 'fs';
import * as path from 'path';
import PDFDocument from 'pdfkit';

export interface ComplianceCheck {
  id?: string;
  checkType: 'soc2' | 'iso27001' | 'gdpr' | 'pci_dss' | 'custom';
  controlId: string;
  controlName: string;
  status: 'pass' | 'fail' | 'warning' | 'not_applicable' | 'pending';
  description: string;
  evidence: string[];
  remediationSteps: string[];
  dueDate?: Date;
  assignee?: string;
  lastChecked: Date;
  nextCheck: Date;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  automatedCheck: boolean;
  metadata?: any;
}

export interface ComplianceReport {
  id: string;
  type: 'soc2' | 'iso27001' | 'gdpr' | 'pci_dss' | 'gap_analysis' | 'audit_readiness';
  title: string;
  description: string;
  generatedAt: Date;
  reportingPeriod: {
    startDate: Date;
    endDate: Date;
  };
  summary: {
    totalControls: number;
    passingControls: number;
    failingControls: number;
    warningControls: number;
    complianceScore: number;
  };
  sections: ComplianceReportSection[];
  recommendations: string[];
  findings: ComplianceFinding[];
  attachments: string[];
  metadata?: any;
}

export interface ComplianceReportSection {
  title: string;
  description: string;
  controls: ComplianceCheck[];
  summary: {
    totalControls: number;
    passingControls: number;
    compliancePercentage: number;
  };
}

export interface ComplianceFinding {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  controls: string[];
  evidence: string[];
  recommendation: string;
  remediation: {
    steps: string[];
    estimatedEffort: string;
    priority: number;
    dueDate?: Date;
  };
}

export interface AuditTrail {
  id: string;
  userId?: string;
  action: string;
  resource: string;
  timestamp: Date;
  ipAddress: string;
  userAgent: string;
  outcome: 'success' | 'failure';
  details: any;
  retentionPeriod: number; // days
}

/**
 * Compliance Management System
 * 
 * Provides comprehensive compliance automation for:
 * - SOC 2 Type 2 compliance
 * - ISO 27001 certification
 * - GDPR/CCPA data protection
 * - PCI DSS payment security
 * - Custom compliance frameworks
 */
export class ComplianceManager extends EventEmitter {
  private pool: Pool;
  private redis: Redis.RedisClientType;
  private logger: winston.Logger;
  private controlFrameworks: Map<string, any>;

  // Compliance frameworks configuration
  private readonly FRAMEWORKS = {
    soc2: {
      name: 'SOC 2 Type 2',
      version: '2017',
      categories: ['security', 'availability', 'processing_integrity', 'confidentiality', 'privacy'],
      retentionPeriod: 2555, // 7 years
    },
    iso27001: {
      name: 'ISO/IEC 27001:2013',
      version: '2013',
      categories: ['information_security_policies', 'organization_security', 'human_resource_security', 
                  'asset_management', 'access_control', 'cryptography', 'physical_security',
                  'operations_security', 'communications_security', 'acquisition', 'supplier_relationships',
                  'incident_management', 'business_continuity', 'compliance'],
      retentionPeriod: 2555, // 7 years
    },
    gdpr: {
      name: 'General Data Protection Regulation',
      version: '2018',
      categories: ['lawfulness', 'purpose_limitation', 'data_minimization', 'accuracy', 
                  'storage_limitation', 'integrity', 'accountability'],
      retentionPeriod: 2555, // 7 years
    },
    pci_dss: {
      name: 'Payment Card Industry Data Security Standard',
      version: '4.0',
      categories: ['network_security', 'cardholder_data', 'vulnerability_management',
                  'access_control', 'monitoring', 'information_security_policies'],
      retentionPeriod: 1095, // 3 years
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
        new winston.transports.File({ filename: 'logs/compliance.log' }),
      ],
    });
    this.controlFrameworks = new Map();

    this.initializeControlFrameworks();
  }

  /**
   * Initialize compliance control frameworks
   */
  private async initializeControlFrameworks(): Promise<void> {
    // Load SOC 2 controls
    this.controlFrameworks.set('soc2', {
      controls: [
        {
          id: 'CC1.1',
          name: 'Control Environment',
          description: 'The entity demonstrates a commitment to integrity and ethical values',
          category: 'security',
          riskLevel: 'high',
          automated: true,
        },
        {
          id: 'CC2.1',
          name: 'Communication and Information',
          description: 'The entity obtains or generates and uses relevant, quality information',
          category: 'security',
          riskLevel: 'medium',
          automated: true,
        },
        {
          id: 'CC3.1',
          name: 'Risk Assessment',
          description: 'The entity specifies objectives with sufficient clarity',
          category: 'security',
          riskLevel: 'high',
          automated: false,
        },
        {
          id: 'CC4.1',
          name: 'Control Activities',
          description: 'The entity selects and develops control activities',
          category: 'security',
          riskLevel: 'high',
          automated: true,
        },
        {
          id: 'CC5.1',
          name: 'Monitoring',
          description: 'The entity selects, develops, and performs ongoing evaluations',
          category: 'security',
          riskLevel: 'medium',
          automated: true,
        },
        // Add more SOC 2 controls...
      ],
    });

    // Load ISO 27001 controls
    this.controlFrameworks.set('iso27001', {
      controls: [
        {
          id: 'A.5.1.1',
          name: 'Information Security Policy',
          description: 'Management direction and support for information security',
          category: 'information_security_policies',
          riskLevel: 'high',
          automated: false,
        },
        {
          id: 'A.6.1.1',
          name: 'Information Security Roles and Responsibilities',
          description: 'Information security responsibilities defined and allocated',
          category: 'organization_security',
          riskLevel: 'high',
          automated: false,
        },
        {
          id: 'A.9.1.1',
          name: 'Access Control Policy',
          description: 'Access control policy established, documented and reviewed',
          category: 'access_control',
          riskLevel: 'critical',
          automated: true,
        },
        {
          id: 'A.12.6.1',
          name: 'Management of Technical Vulnerabilities',
          description: 'Information about technical vulnerabilities',
          category: 'operations_security',
          riskLevel: 'high',
          automated: true,
        },
        // Add more ISO 27001 controls...
      ],
    });

    // Load GDPR requirements
    this.controlFrameworks.set('gdpr', {
      controls: [
        {
          id: 'Art.5',
          name: 'Principles of Processing',
          description: 'Personal data shall be processed lawfully, fairly and transparently',
          category: 'lawfulness',
          riskLevel: 'critical',
          automated: true,
        },
        {
          id: 'Art.25',
          name: 'Data Protection by Design and by Default',
          description: 'Appropriate technical and organisational measures',
          category: 'accountability',
          riskLevel: 'high',
          automated: true,
        },
        {
          id: 'Art.30',
          name: 'Records of Processing Activities',
          description: 'Each controller shall maintain a record',
          category: 'accountability',
          riskLevel: 'high',
          automated: false,
        },
        {
          id: 'Art.32',
          name: 'Security of Processing',
          description: 'Appropriate technical and organisational measures',
          category: 'integrity',
          riskLevel: 'critical',
          automated: true,
        },
        // Add more GDPR requirements...
      ],
    });

    this.logger.info(`Initialized ${this.controlFrameworks.size} compliance frameworks`);
  }

  /**
   * Run compliance check for specific control
   */
  public async runComplianceCheck(data: {
    checkType: string;
    controlId: string;
    automated?: boolean;
  }): Promise<ComplianceCheck> {
    try {
      const framework = this.controlFrameworks.get(data.checkType);
      if (!framework) {
        throw new Error(`Unknown compliance framework: ${data.checkType}`);
      }

      const control = framework.controls.find((c: any) => c.id === data.controlId);
      if (!control) {
        throw new Error(`Unknown control: ${data.controlId}`);
      }

      let result: ComplianceCheck;

      if (control.automated && (data.automated !== false)) {
        result = await this.runAutomatedCheck(data.checkType, control);
      } else {
        result = await this.createManualCheck(data.checkType, control);
      }

      // Store check result
      await this.storeComplianceCheck(result);

      // Schedule next check
      await this.scheduleNextCheck(result);

      this.logger.info('Compliance check completed', {
        checkType: data.checkType,
        controlId: data.controlId,
        status: result.status,
      });

      return result;

    } catch (error) {
      this.logger.error('Compliance check error:', error);
      throw error;
    }
  }

  /**
   * Run automated compliance check
   */
  private async runAutomatedCheck(checkType: string, control: any): Promise<ComplianceCheck> {
    const checkResult: ComplianceCheck = {
      checkType: checkType as any,
      controlId: control.id,
      controlName: control.name,
      status: 'pending',
      description: control.description,
      evidence: [],
      remediationSteps: [],
      lastChecked: new Date(),
      nextCheck: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
      riskLevel: control.riskLevel,
      automatedCheck: true,
    };

    // Run specific automated checks based on control type
    switch (control.id) {
      case 'CC1.1': // SOC 2 - Control Environment
        const controlEnvResult = await this.checkControlEnvironment();
        checkResult.status = controlEnvResult.status;
        checkResult.evidence = controlEnvResult.evidence;
        break;

      case 'A.9.1.1': // ISO 27001 - Access Control Policy
        const accessControlResult = await this.checkAccessControlPolicy();
        checkResult.status = accessControlResult.status;
        checkResult.evidence = accessControlResult.evidence;
        break;

      case 'Art.5': // GDPR - Principles of Processing
        const gdprPrinciplesResult = await this.checkGDPRPrinciples();
        checkResult.status = gdprPrinciplesResult.status;
        checkResult.evidence = gdprPrinciplesResult.evidence;
        break;

      case 'Art.32': // GDPR - Security of Processing
        const securityProcessingResult = await this.checkSecurityOfProcessing();
        checkResult.status = securityProcessingResult.status;
        checkResult.evidence = securityProcessingResult.evidence;
        break;

      default:
        checkResult.status = 'not_applicable';
        checkResult.evidence = ['Automated check not implemented for this control'];
        break;
    }

    // Add remediation steps if check failed
    if (checkResult.status === 'fail') {
      checkResult.remediationSteps = this.generateRemediationSteps(control);
      checkResult.dueDate = new Date(Date.now() + this.getRemediationTimeframe(control.riskLevel));
    }

    return checkResult;
  }

  /**
   * Create manual compliance check
   */
  private async createManualCheck(checkType: string, control: any): Promise<ComplianceCheck> {
    return {
      checkType: checkType as any,
      controlId: control.id,
      controlName: control.name,
      status: 'pending',
      description: control.description,
      evidence: [],
      remediationSteps: [],
      lastChecked: new Date(),
      nextCheck: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), // 90 days
      riskLevel: control.riskLevel,
      automatedCheck: false,
      assignee: 'compliance_team',
      dueDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000), // 14 days
    };
  }

  /**
   * Automated check: Control Environment (SOC 2 CC1.1)
   */
  private async checkControlEnvironment(): Promise<{ status: any; evidence: string[] }> {
    const evidence: string[] = [];
    let passed = 0;
    const totalChecks = 4;

    // Check if code of conduct exists
    if (await this.checkDocumentExists('code_of_conduct')) {
      evidence.push('Code of conduct documented and accessible');
      passed++;
    } else {
      evidence.push('❌ Code of conduct not found');
    }

    // Check security policies
    if (await this.checkDocumentExists('security_policy')) {
      evidence.push('Security policies documented and current');
      passed++;
    } else {
      evidence.push('❌ Security policies not found or outdated');
    }

    // Check employee background checks
    const backgroundCheckCompliance = await this.checkBackgroundCheckCompliance();
    if (backgroundCheckCompliance > 90) {
      evidence.push(`Background checks completed for ${backgroundCheckCompliance}% of employees`);
      passed++;
    } else {
      evidence.push(`❌ Background checks only completed for ${backgroundCheckCompliance}% of employees`);
    }

    // Check security awareness training
    const trainingCompliance = await this.checkSecurityTrainingCompliance();
    if (trainingCompliance > 85) {
      evidence.push(`Security awareness training completed by ${trainingCompliance}% of employees`);
      passed++;
    } else {
      evidence.push(`❌ Security awareness training only completed by ${trainingCompliance}% of employees`);
    }

    const compliancePercentage = (passed / totalChecks) * 100;
    let status: 'pass' | 'warning' | 'fail';

    if (compliancePercentage >= 90) {
      status = 'pass';
    } else if (compliancePercentage >= 70) {
      status = 'warning';
    } else {
      status = 'fail';
    }

    return { status, evidence };
  }

  /**
   * Automated check: Access Control Policy (ISO 27001 A.9.1.1)
   */
  private async checkAccessControlPolicy(): Promise<{ status: any; evidence: string[] }> {
    const evidence: string[] = [];
    let passed = 0;
    const totalChecks = 5;

    // Check if access control policy exists and is current
    if (await this.checkDocumentExists('access_control_policy', 365)) {
      evidence.push('Access control policy documented and reviewed within last year');
      passed++;
    } else {
      evidence.push('❌ Access control policy missing or outdated');
    }

    // Check role-based access control implementation
    const rbacCompliance = await this.checkRBACImplementation();
    if (rbacCompliance > 95) {
      evidence.push(`RBAC implemented for ${rbacCompliance}% of systems`);
      passed++;
    } else {
      evidence.push(`❌ RBAC only implemented for ${rbacCompliance}% of systems`);
    }

    // Check access reviews
    const accessReviewCompliance = await this.checkAccessReviews();
    if (accessReviewCompliance > 90) {
      evidence.push(`Access reviews completed for ${accessReviewCompliance}% of users`);
      passed++;
    } else {
      evidence.push(`❌ Access reviews only completed for ${accessReviewCompliance}% of users`);
    }

    // Check privileged access management
    const pamCompliance = await this.checkPrivilegedAccessManagement();
    if (pamCompliance > 85) {
      evidence.push(`Privileged access properly managed for ${pamCompliance}% of admin accounts`);
      passed++;
    } else {
      evidence.push(`❌ Privileged access management gaps for ${100 - pamCompliance}% of admin accounts`);
    }

    // Check multi-factor authentication
    const mfaCompliance = await this.checkMFACompliance();
    if (mfaCompliance > 95) {
      evidence.push(`MFA enabled for ${mfaCompliance}% of user accounts`);
      passed++;
    } else {
      evidence.push(`❌ MFA only enabled for ${mfaCompliance}% of user accounts`);
    }

    const compliancePercentage = (passed / totalChecks) * 100;
    let status: 'pass' | 'warning' | 'fail';

    if (compliancePercentage >= 90) {
      status = 'pass';
    } else if (compliancePercentage >= 70) {
      status = 'warning';
    } else {
      status = 'fail';
    }

    return { status, evidence };
  }

  /**
   * Automated check: GDPR Principles (Art. 5)
   */
  private async checkGDPRPrinciples(): Promise<{ status: any; evidence: string[] }> {
    const evidence: string[] = [];
    let passed = 0;
    const totalChecks = 6;

    // Lawfulness, fairness and transparency
    const consentCompliance = await this.checkConsentManagement();
    if (consentCompliance > 95) {
      evidence.push(`Consent management implemented with ${consentCompliance}% compliance`);
      passed++;
    } else {
      evidence.push(`❌ Consent management gaps: ${100 - consentCompliance}% non-compliance`);
    }

    // Purpose limitation
    const purposeLimitationCompliance = await this.checkPurposeLimitation();
    if (purposeLimitationCompliance > 90) {
      evidence.push('Purpose limitation controls implemented');
      passed++;
    } else {
      evidence.push('❌ Purpose limitation controls inadequate');
    }

    // Data minimization
    const dataMinimizationCompliance = await this.checkDataMinimization();
    if (dataMinimizationCompliance > 85) {
      evidence.push('Data minimization practices in place');
      passed++;
    } else {
      evidence.push('❌ Data minimization practices insufficient');
    }

    // Accuracy
    const dataAccuracyCompliance = await this.checkDataAccuracy();
    if (dataAccuracyCompliance > 90) {
      evidence.push('Data accuracy controls implemented');
      passed++;
    } else {
      evidence.push('❌ Data accuracy controls inadequate');
    }

    // Storage limitation
    const retentionCompliance = await this.checkDataRetentionPolicies();
    if (retentionCompliance > 90) {
      evidence.push('Data retention policies properly implemented');
      passed++;
    } else {
      evidence.push('❌ Data retention policies inadequate');
    }

    // Integrity and confidentiality
    const encryptionCompliance = await this.checkEncryptionCompliance();
    if (encryptionCompliance > 95) {
      evidence.push(`Data encryption implemented with ${encryptionCompliance}% compliance`);
      passed++;
    } else {
      evidence.push(`❌ Data encryption gaps: ${100 - encryptionCompliance}% non-compliance`);
    }

    const compliancePercentage = (passed / totalChecks) * 100;
    let status: 'pass' | 'warning' | 'fail';

    if (compliancePercentage >= 95) {
      status = 'pass';
    } else if (compliancePercentage >= 80) {
      status = 'warning';
    } else {
      status = 'fail';
    }

    return { status, evidence };
  }

  /**
   * Automated check: Security of Processing (GDPR Art. 32)
   */
  private async checkSecurityOfProcessing(): Promise<{ status: any; evidence: string[] }> {
    const evidence: string[] = [];
    let passed = 0;
    const totalChecks = 4;

    // Encryption of personal data
    const encryptionScore = await this.checkEncryptionCompliance();
    if (encryptionScore > 95) {
      evidence.push(`Personal data encrypted with ${encryptionScore}% coverage`);
      passed++;
    } else {
      evidence.push(`❌ Personal data encryption gaps: ${100 - encryptionScore}% uncovered`);
    }

    // Ongoing confidentiality, integrity, availability
    const securityControlsScore = await this.checkSecurityControls();
    if (securityControlsScore > 90) {
      evidence.push(`Security controls operational with ${securityControlsScore}% effectiveness`);
      passed++;
    } else {
      evidence.push(`❌ Security controls inadequate: ${100 - securityControlsScore}% gaps`);
    }

    // Regular testing and evaluation
    const testingCompliance = await this.checkSecurityTesting();
    if (testingCompliance > 85) {
      evidence.push(`Security testing conducted with ${testingCompliance}% compliance`);
      passed++;
    } else {
      evidence.push(`❌ Security testing insufficient: ${100 - testingCompliance}% gaps`);
    }

    // Incident response and breach notification
    const incidentResponseScore = await this.checkIncidentResponse();
    if (incidentResponseScore > 90) {
      evidence.push(`Incident response capabilities at ${incidentResponseScore}% effectiveness`);
      passed++;
    } else {
      evidence.push(`❌ Incident response gaps: ${100 - incidentResponseScore}% inadequate`);
    }

    const compliancePercentage = (passed / totalChecks) * 100;
    let status: 'pass' | 'warning' | 'fail';

    if (compliancePercentage >= 95) {
      status = 'pass';
    } else if (compliancePercentage >= 80) {
      status = 'warning';
    } else {
      status = 'fail';
    }

    return { status, evidence };
  }

  /**
   * Generate compliance report
   */
  public async generateComplianceReport(
    type: 'soc2' | 'iso27001' | 'gdpr' | 'pci_dss' | 'gap_analysis' | 'audit_readiness',
    filters: any = {}
  ): Promise<ComplianceReport> {
    try {
      const reportPeriod = {
        startDate: filters.startDate ? new Date(filters.startDate) : new Date(Date.now() - 90 * 24 * 60 * 60 * 1000),
        endDate: filters.endDate ? new Date(filters.endDate) : new Date(),
      };

      let checks: ComplianceCheck[];
      let title: string;
      let description: string;

      if (type === 'gap_analysis') {
        checks = await this.getAllComplianceChecks();
        title = 'Compliance Gap Analysis Report';
        description = 'Comprehensive analysis of compliance gaps across all frameworks';
      } else if (type === 'audit_readiness') {
        checks = await this.getAuditReadinessChecks();
        title = 'Audit Readiness Assessment';
        description = 'Assessment of readiness for external compliance audits';
      } else {
        checks = await this.getComplianceChecksByType(type);
        title = `${this.FRAMEWORKS[type]?.name || type} Compliance Report`;
        description = `Compliance status report for ${this.FRAMEWORKS[type]?.name || type}`;
      }

      // Filter checks by reporting period
      const filteredChecks = checks.filter(check => 
        check.lastChecked >= reportPeriod.startDate &&
        check.lastChecked <= reportPeriod.endDate
      );

      // Calculate summary metrics
      const summary = {
        totalControls: filteredChecks.length,
        passingControls: filteredChecks.filter(c => c.status === 'pass').length,
        failingControls: filteredChecks.filter(c => c.status === 'fail').length,
        warningControls: filteredChecks.filter(c => c.status === 'warning').length,
        complianceScore: 0,
      };

      summary.complianceScore = summary.totalControls > 0 
        ? Math.round((summary.passingControls / summary.totalControls) * 100)
        : 0;

      // Group checks by category
      const sections = this.groupChecksByCategory(filteredChecks, type);

      // Generate findings
      const findings = await this.generateFindings(filteredChecks);

      // Generate recommendations
      const recommendations = this.generateRecommendations(filteredChecks, findings);

      const report: ComplianceReport = {
        id: `report_${Date.now()}`,
        type,
        title,
        description,
        generatedAt: new Date(),
        reportingPeriod,
        summary,
        sections,
        recommendations,
        findings,
        attachments: [],
      };

      // Generate PDF report
      const pdfPath = await this.generatePDFReport(report);
      report.attachments.push(pdfPath);

      // Store report
      await this.storeComplianceReport(report);

      this.logger.info('Compliance report generated', {
        type,
        reportId: report.id,
        complianceScore: summary.complianceScore,
      });

      return report;

    } catch (error) {
      this.logger.error('Compliance report generation error:', error);
      throw error;
    }
  }

  /**
   * Get compliance checks with filtering
   */
  public async getComplianceChecks(filters: any = {}): Promise<{
    checks: ComplianceCheck[];
    totalCount: number;
    page: number;
    pageSize: number;
  }> {
    const page = parseInt(filters.page || '1', 10);
    const pageSize = Math.min(parseInt(filters.pageSize || '100', 10), 1000);
    const offset = (page - 1) * pageSize;

    let whereClause = '1=1';
    const values: any[] = [];

    if (filters.checkType) {
      whereClause += ` AND check_type = $${values.length + 1}`;
      values.push(filters.checkType);
    }

    if (filters.status) {
      whereClause += ` AND status = $${values.length + 1}`;
      values.push(filters.status);
    }

    if (filters.riskLevel) {
      whereClause += ` AND risk_level = $${values.length + 1}`;
      values.push(filters.riskLevel);
    }

    if (filters.assignee) {
      whereClause += ` AND assignee = $${values.length + 1}`;
      values.push(filters.assignee);
    }

    // Get total count
    const countResult = await this.pool.query(
      `SELECT COUNT(*) FROM security.compliance_checks WHERE ${whereClause}`,
      values,
    );
    const totalCount = parseInt(countResult.rows[0].count, 10);

    // Get checks
    const checksResult = await this.pool.query(
      `SELECT * FROM security.compliance_checks WHERE ${whereClause} 
       ORDER BY risk_level DESC, last_checked DESC 
       LIMIT $${values.length + 1} OFFSET $${values.length + 2}`,
      [...values, pageSize, offset],
    );

    return {
      checks: checksResult.rows.map(this.mapDatabaseRowToComplianceCheck),
      totalCount,
      page,
      pageSize,
    };
  }

  /**
   * Log audit trail entry
   */
  public async logAuditTrail(entry: Omit<AuditTrail, 'id' | 'timestamp'>): Promise<string> {
    const auditEntry: AuditTrail = {
      id: `audit_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      ...entry,
    };

    await this.pool.query(`
      INSERT INTO security.audit_trail (
        id, user_id, action, resource, timestamp, ip_address, 
        user_agent, outcome, details, retention_period
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
    `, [
      auditEntry.id,
      auditEntry.userId,
      auditEntry.action,
      auditEntry.resource,
      auditEntry.timestamp,
      auditEntry.ipAddress,
      auditEntry.userAgent,
      auditEntry.outcome,
      JSON.stringify(auditEntry.details),
      auditEntry.retentionPeriod,
    ]);

    return auditEntry.id;
  }

  /**
   * Helper methods for compliance checks
   */
  private async checkDocumentExists(documentType: string, maxAgeInDays?: number): Promise<boolean> {
    // Mock implementation - would check document management system
    const documents = ['code_of_conduct', 'security_policy', 'access_control_policy'];
    return documents.includes(documentType);
  }

  private async checkBackgroundCheckCompliance(): Promise<number> {
    // Mock implementation - would check HR system
    return 95; // 95% compliance
  }

  private async checkSecurityTrainingCompliance(): Promise<number> {
    // Mock implementation - would check training system
    return 88; // 88% compliance
  }

  private async checkRBACImplementation(): Promise<number> {
    // Mock implementation - would check access control systems
    return 97; // 97% RBAC implementation
  }

  private async checkAccessReviews(): Promise<number> {
    // Mock implementation - would check access review records
    return 92; // 92% access reviews completed
  }

  private async checkPrivilegedAccessManagement(): Promise<number> {
    // Mock implementation - would check PAM system
    return 89; // 89% PAM compliance
  }

  private async checkMFACompliance(): Promise<number> {
    // Check actual MFA compliance from user accounts
    const result = await this.pool.query(`
      SELECT COUNT(*) as total,
             COUNT(CASE WHEN is_mfa_enabled = true THEN 1 END) as mfa_enabled
      FROM users WHERE is_active = true
    `);

    const { total, mfa_enabled } = result.rows[0];
    return total > 0 ? Math.round((mfa_enabled / total) * 100) : 0;
  }

  private async checkConsentManagement(): Promise<number> {
    // Mock implementation - would check consent management system
    return 96; // 96% consent compliance
  }

  private async checkPurposeLimitation(): Promise<number> {
    // Mock implementation - would check data usage vs declared purposes
    return 91; // 91% purpose limitation compliance
  }

  private async checkDataMinimization(): Promise<number> {
    // Mock implementation - would check data collection practices
    return 87; // 87% data minimization compliance
  }

  private async checkDataAccuracy(): Promise<number> {
    // Mock implementation - would check data quality metrics
    return 93; // 93% data accuracy compliance
  }

  private async checkDataRetentionPolicies(): Promise<number> {
    // Mock implementation - would check retention policy compliance
    return 94; // 94% retention policy compliance
  }

  private async checkEncryptionCompliance(): Promise<number> {
    // Mock implementation - would check encryption coverage
    return 98; // 98% encryption compliance
  }

  private async checkSecurityControls(): Promise<number> {
    // Mock implementation - would check security control effectiveness
    return 92; // 92% security controls operational
  }

  private async checkSecurityTesting(): Promise<number> {
    // Mock implementation - would check security testing records
    return 87; // 87% testing compliance
  }

  private async checkIncidentResponse(): Promise<number> {
    // Mock implementation - would check incident response capabilities
    return 91; // 91% incident response effectiveness
  }

  private generateRemediationSteps(control: any): string[] {
    const steps: { [key: string]: string[] } = {
      'high': [
        'Assign dedicated resource to remediate this control',
        'Conduct immediate gap analysis',
        'Implement interim controls if needed',
        'Develop detailed remediation plan',
        'Execute remediation with weekly progress reviews',
      ],
      'medium': [
        'Assign resource to remediate this control',
        'Conduct gap analysis within 1 week',
        'Develop remediation plan',
        'Execute remediation with bi-weekly progress reviews',
      ],
      'low': [
        'Include in next quarterly review cycle',
        'Assign to appropriate team member',
        'Develop remediation plan within 2 weeks',
      ],
    };

    return steps[control.riskLevel] || steps['medium'];
  }

  private getRemediationTimeframe(riskLevel: string): number {
    const timeframes = {
      'critical': 7 * 24 * 60 * 60 * 1000,  // 7 days
      'high': 14 * 24 * 60 * 60 * 1000,     // 14 days
      'medium': 30 * 24 * 60 * 60 * 1000,   // 30 days
      'low': 90 * 24 * 60 * 60 * 1000,      // 90 days
    };

    return timeframes[riskLevel as keyof typeof timeframes] || timeframes['medium'];
  }

  private async storeComplianceCheck(check: ComplianceCheck): Promise<void> {
    await this.pool.query(`
      INSERT INTO security.compliance_checks (
        check_type, control_id, status, description, evidence, 
        remediation_steps, due_date, assignee, last_checked, risk_level
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
      ON CONFLICT (control_id) 
      UPDATE SET status = $3, evidence = $5, last_checked = $9, updated_at = NOW()
    `, [
      check.checkType,
      check.controlId,
      check.status,
      check.description,
      check.evidence,
      check.remediationSteps,
      check.dueDate,
      check.assignee,
      check.lastChecked,
      check.riskLevel,
    ]);
  }

  private async scheduleNextCheck(check: ComplianceCheck): Promise<void> {
    // Schedule next automated check based on risk level and type
    const intervals = {
      'critical': 7,    // days
      'high': 14,
      'medium': 30,
      'low': 90,
    };

    const interval = intervals[check.riskLevel as keyof typeof intervals] || 30;
    check.nextCheck = new Date(Date.now() + interval * 24 * 60 * 60 * 1000);
  }

  private async getAllComplianceChecks(): Promise<ComplianceCheck[]> {
    const result = await this.pool.query('SELECT * FROM security.compliance_checks');
    return result.rows.map(this.mapDatabaseRowToComplianceCheck);
  }

  private async getAuditReadinessChecks(): Promise<ComplianceCheck[]> {
    const result = await this.pool.query(`
      SELECT * FROM security.compliance_checks 
      WHERE status IN ('fail', 'warning') OR due_date < NOW() + INTERVAL '30 days'
    `);
    return result.rows.map(this.mapDatabaseRowToComplianceCheck);
  }

  private async getComplianceChecksByType(type: string): Promise<ComplianceCheck[]> {
    const result = await this.pool.query(
      'SELECT * FROM security.compliance_checks WHERE check_type = $1',
      [type]
    );
    return result.rows.map(this.mapDatabaseRowToComplianceCheck);
  }

  private groupChecksByCategory(checks: ComplianceCheck[], type: string): ComplianceReportSection[] {
    // Implementation would group checks by framework-specific categories
    return [];
  }

  private async generateFindings(checks: ComplianceCheck[]): Promise<ComplianceFinding[]> {
    // Implementation would analyze failed checks and generate findings
    return [];
  }

  private generateRecommendations(checks: ComplianceCheck[], findings: ComplianceFinding[]): string[] {
    // Implementation would generate actionable recommendations
    return [
      'Implement automated compliance monitoring',
      'Establish regular compliance review processes',
      'Provide compliance training to all staff',
    ];
  }

  private async generatePDFReport(report: ComplianceReport): Promise<string> {
    // Implementation would generate PDF using PDFKit or similar
    return `reports/${report.id}.pdf`;
  }

  private async storeComplianceReport(report: ComplianceReport): Promise<void> {
    // Implementation would store report in database
    this.logger.debug('Compliance report stored', { reportId: report.id });
  }

  private mapDatabaseRowToComplianceCheck(row: any): ComplianceCheck {
    return {
      id: row.id,
      checkType: row.check_type,
      controlId: row.control_id,
      controlName: row.control_name || '',
      status: row.status,
      description: row.description,
      evidence: row.evidence || [],
      remediationSteps: row.remediation_steps || [],
      dueDate: row.due_date,
      assignee: row.assignee,
      lastChecked: row.last_checked,
      nextCheck: row.next_check,
      riskLevel: row.risk_level,
      automatedCheck: row.automated_check,
      metadata: row.metadata,
    };
  }

  public async checkHealth(): Promise<string> {
    try {
      await this.pool.query('SELECT 1');
      return 'healthy';
    } catch (error) {
      this.logger.error('Compliance manager health check failed:', error);
      return 'unhealthy';
    }
  }
}