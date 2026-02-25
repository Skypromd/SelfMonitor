#!/usr/bin/env python3
"""
Enterprise Alert Management System
Multi-channel notifications for critical database events
"""

import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self):
        self.webhook_url = os.getenv('ALERT_WEBHOOK_URL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.pagerduty_key = os.getenv('PAGERDUTY_KEY')
        self.smtp_host = os.getenv('EMAIL_SMTP_HOST')
        self.smtp_port = int(os.getenv('EMAIL_SMTP_PORT', 587))
        self.email_user = os.getenv('EMAIL_USERNAME')
        self.email_pass = os.getenv('EMAIL_PASSWORD')
        self.alert_email = os.getenv('ALERT_EMAIL')
        
        logger.info("AlertManager initialized")
    
    def send_slack_alert(self, title, message, color="danger"):
        """Send alert to Slack"""
        if not self.slack_webhook:
            return False
        
        try:
            payload = {
                "attachments": [{
                    "title": title,
                    "text": message,
                    "color": color,
                    "ts": int(datetime.now().timestamp())
                }]
            }
            
            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.error(f"Slack alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Slack alert error: {e}")
            return False
    
    def send_pagerduty_alert(self, title, message, severity="critical"):
        """Send alert to PagerDuty"""
        if not self.pagerduty_key:
            return False
        
        try:
            payload = {
                "routing_key": self.pagerduty_key,
                "event_action": "trigger",
                "dedup_key": f"selfmonitor-db-{datetime.now().strftime('%Y%m%d')}",
                "payload": {
                    "summary": title,
                    "source": "SelfMonitor Database Monitor",
                    "severity": severity,
                    "custom_details": {
                        "message": message,
                        "timestamp": datetime.now().isoformat(),
                        "component": "database"
                    }
                }
            }
            
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 202:
                logger.info("PagerDuty alert sent successfully")
                return True
            else:
                logger.error(f"PagerDuty alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"PagerDuty alert error: {e}")
            return False
    
    def send_email_alert(self, title, message):
        """Send alert via email"""
        if not all([self.smtp_host, self.email_user, self.email_pass, self.alert_email]):
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = self.alert_email
            msg['Subject'] = f"[SelfMonitor Alert] {title}"
            
            body = f"""
            SelfMonitor Database Alert
            
            {title}
            
            {message}
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
            System: SelfMonitor FinTech Platform
            Component: Database Infrastructure
            
            This is an automated alert from the SelfMonitor monitoring system.
            Please investigate immediately if this is a critical alert.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_pass)
            text = msg.as_string()
            server.sendmail(self.email_user, self.alert_email, text)
            server.quit()
            
            logger.info("Email alert sent successfully")
            return True
        except Exception as e:
            logger.error(f"Email alert error: {e}")
            return False
    
    def send_webhook_alert(self, title, message, level="alert"):
        """Send alert to custom webhook"""
        if not self.webhook_url:
            return False
        
        try:
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "timestamp": datetime.now().isoformat(),
                "source": "selfmonitor-db-monitor",
                "component": "database"
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Webhook alert sent successfully")
                return True
            else:
                logger.error(f"Webhook alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Webhook alert error: {e}")
            return False
    
    def send_critical_alert(self, title, message):
        """Send critical alert to all channels"""
        logger.critical(f"CRITICAL ALERT: {title} - {message}")
        
        # Send to all available channels
        self.send_slack_alert(title, message, color="danger")
        self.send_pagerduty_alert(title, message, severity="critical")
        self.send_email_alert(title, message)
        self.send_webhook_alert(title, message, level="critical")
    
    def send_warning_alert(self, title, message):
        """Send warning alert"""
        logger.warning(f"WARNING: {title} - {message}")
        
        self.send_slack_alert(title, message, color="warning")
        self.send_webhook_alert(title, message, level="warning")
    
    def send_recovery_alert(self, title, message):
        """Send recovery notification"""
        logger.info(f"RECOVERY: {title} - {message}")
        
        self.send_slack_alert(title, message, color="good")
        self.send_webhook_alert(title, message, level="recovery")
    
    def send_info_alert(self, title, message):
        """Send informational alert"""
        logger.info(f"INFO: {title} - {message}")
        
        self.send_slack_alert(title, message, color="good")
        self.send_webhook_alert(title, message, level="info")