"""
Notification System for MLOps Platform
Handles alerts and notifications via multiple channels
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

import aiohttp
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from .config import MLOpsConfig

logger = logging.getLogger(__name__)

class NotificationChannel:
    """Base class for notification channels"""
    
    async def send_message(
        self,
        message: str,
        title: Optional[str] = None,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification message"""
        raise NotImplementedError


class SlackNotifier(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None):
        self.webhook_url = webhook_url
        self.client = AsyncWebClient(token=bot_token) if bot_token else None
        
    async def send_message(
        self,
        message: str,
        channel: str = "#ml-ops",
        title: Optional[str] = None,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send message to Slack"""
        try:
            # Prepare message payload
            if self.client:
                # Use Bot API
                await self._send_via_bot_api(message, channel, title, severity, metadata)
            elif self.webhook_url:
                # Use Webhook
                await self._send_via_webhook(message, title, severity, metadata)
            else:
                logger.warning("No Slack credentials configured")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
            
    async def _send_via_bot_api(
        self,
        message: str,
        channel: str,
        title: Optional[str],
        severity: str,
        metadata: Optional[Dict[str, Any]]
    ):
        """Send notification using Slack Bot API"""
        try:
            # Choose emoji based on severity
            emoji_map = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨"
            }
            
            emoji = emoji_map.get(severity, "ℹ️")
            
            # Create blocks for rich formatting
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{title or 'MLOps Notification'}*\n{message}"
                    }
                }
            ]
            
            # Add metadata fields if provided
            if metadata:
                fields = []
                for key, value in metadata.items():
                    fields.append({
                        "type": "mrkdwn",
                        "text": f"*{key}:*\n{value}"
                    })
                    
                if fields:
                    blocks.append({
                        "type": "section",
                        "fields": fields[:10]  # Slack limits to 10 fields
                    })
                    
            # Add timestamp
            blocks.append({
                "type": "context",
                "elements": [{
                    "type": "plain_text",
                    "text": f"Sent at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }]
            })
            
            await self.client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=title or "MLOps Notification"  # Fallback text
            )
            
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            raise
            
    async def _send_via_webhook(
        self,
        message: str,
        title: Optional[str],
        severity: str,
        metadata: Optional[Dict[str, Any]]
    ):
        """Send notification using Slack Webhook"""
        try:
            # Choose color based on severity
            color_map = {
                "info": "#36a64f",      # green
                "success": "#36a64f",   # green
                "warning": "#ffaa00",   # orange  
                "error": "#ff0000",     # red
                "critical": "#ff0000"   # red
            }
            
            color = color_map.get(severity, "#36a64f")
            
            # Create attachment
            attachment = {
                "color": color,
                "title": title or "MLOps Notification",
                "text": message,
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }
            
            # Add metadata fields
            if metadata:
                fields = []
                for key, value in metadata.items():
                    fields.append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
                attachment["fields"] = fields[:10]
                
            payload = {
                "attachments": [attachment]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Webhook request failed: {response.status}")
                        
        except Exception as e:
            logger.error(f"Slack webhook error: {str(e)}")
            raise


class EmailNotifier(NotificationChannel):
    """Email notification channel"""
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        
    async def send_message(
        self,
        message: str,
        to_emails: List[str],
        title: Optional[str] = None,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send email notification"""
        try:
            # Create message
            msg = MimeMultipart("alternative")
            msg["Subject"] = title or "MLOps Notification"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_emails)
            
            # Create HTML content
            html_content = self._create_html_content(message, severity, metadata)
            
            # Create plain text content
            text_content = self._create_text_content(message, metadata)
            
            # Attach parts
            text_part = MimeText(text_content, "plain")
            html_part = MimeText(html_content, "html")
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            await asyncio.get_event_loop().run_in_executor(
                None,
                self._send_email,
                msg,
                to_emails
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {str(e)}")
            return False
            
    def _send_email(self, msg: MimeMultipart, to_emails: List[str]):
        """Send email synchronously"""
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg, to_addresses=to_emails)
            
    def _create_html_content(
        self,
        message: str,
        severity: str,
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Create HTML email content"""
        # Color scheme based on severity
        color_map = {
            "info": "#17a2b8",      # blue
            "success": "#28a745",   # green
            "warning": "#ffc107",   # yellow
            "error": "#dc3545",     # red
            "critical": "#dc3545"   # red
        }
        
        color = color_map.get(severity, "#17a2b8")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>MLOps Notification</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    line-height: 1.6; 
                    color: #333;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: #f9f9f9;
                    border-radius: 10px;
                    overflow: hidden;
                }}
                .header {{ 
                    background: {color}; 
                    color: white; 
                    padding: 20px; 
                    text-align: center;
                }}
                .content {{ 
                    padding: 20px; 
                    background: white;
                }}
                .metadata {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    margin-top: 20px;
                    border-radius: 5px;
                }}
                .metadata-item {{ 
                    margin-bottom: 10px;
                }}
                .metadata-key {{ 
                    font-weight: bold; 
                    color: #495057;
                }}
                .footer {{ 
                    padding: 20px; 
                    text-align: center; 
                    background: #e9ecef;
                    color: #6c757d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>MLOps Notification - {severity.upper()}</h2>
                </div>
                <div class="content">
                    <div style="white-space: pre-line;">{message}</div>
        """
        
        if metadata:
            html += """
                    <div class="metadata">
                        <h4>Additional Information:</h4>
            """
            for key, value in metadata.items():
                html += f"""
                        <div class="metadata-item">
                            <span class="metadata-key">{key}:</span> {value}
                        </div>
                """
            html += "</div>"
            
        html += f"""
                </div>
                <div class="footer">
                    SelfMonitor MLOps Platform<br>
                    Sent at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
        
    def _create_text_content(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Create plain text email content"""
        content = f"MLOps Platform Notification\n\n{message}\n\n"
        
        if metadata:
            content += "Additional Information:\n"
            for key, value in metadata.items():
                content += f"  {key}: {value}\n"
            content += "\n"
            
        content += f"Sent at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        content += "SelfMonitor MLOps Platform"
        
        return content


class NotificationManager:
    """
    Manages multiple notification channels and routing
    """
    
    def __init__(self, config: MLOpsConfig):
        self.config = config
        self.channels = {}
        
        # Initialize notification channels
        self._initialize_channels()
        
    def _initialize_channels(self):
        """Initialize available notification channels"""
        # Slack
        if self.config.slack_webhook_url:
            self.channels["slack"] = SlackNotifier(webhook_url=self.config.slack_webhook_url)
            
        # Email
        if all([
            self.config.email_smtp_server,
            self.config.email_username,
            self.config.email_password
        ]):
            self.channels["email"] = EmailNotifier(
                smtp_server=self.config.email_smtp_server,
                smtp_port=self.config.email_smtp_port,
                username=self.config.email_username,
                password=self.config.email_password,
                from_email=self.config.email_username
            )
            
    async def send_notification(
        self,
        message: str,
        title: Optional[str] = None,
        severity: str = "info",
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Send notification to specified channels"""
        if channels is None:
            channels = list(self.channels.keys())
            
        results = {}
        
        for channel_name in channels:
            if channel_name not in self.channels:
                logger.warning(f"Notification channel '{channel_name}' not configured")
                continue
                
            try:
                channel = self.channels[channel_name]
                
                if channel_name == "slack":
                    result = await channel.send_message(
                        message=message,
                        title=title,
                        severity=severity,
                        metadata=metadata
                    )
                elif channel_name == "email":
                    # For email, you'd need to specify recipients
                    # This is a simplified version
                    admin_emails = ["admin@selfmonitor.com"]  # Configure as needed
                    result = await channel.send_message(
                        message=message,
                        to_emails=admin_emails,
                        title=title,
                        severity=severity,
                        metadata=metadata
                    )
                else:
                    result = await channel.send_message(
                        message=message,
                        title=title,
                        severity=severity,
                        metadata=metadata
                    )
                    
                results[channel_name] = result
                
            except Exception as e:
                logger.error(f"Failed to send notification via {channel_name}: {str(e)}")
                results[channel_name] = False
                
        return results
        
    async def send_model_deployment_success(
        self,
        model_name: str,
        version: str,
        environment: str = "production"
    ):
        """Send model deployment success notification"""
        await self.send_notification(
            message=f"Model {model_name} version {version} successfully deployed to {environment}",
            title="🚀 Model Deployment Success",
            severity="success",
            metadata={
                "Model Name": model_name,
                "Version": version,
                "Environment": environment,
                "Deployment Time": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        )
        
    async def send_model_deployment_failure(
        self,
        model_name: str,
        version: str,
        error: str,
        environment: str = "production"
    ):
        """Send model deployment failure notification"""
        await self.send_notification(
            message=f"Failed to deploy model {model_name} version {version} to {environment}.\n\nError: {error}",
            title="❌ Model Deployment Failed",
            severity="error",
            metadata={
                "Model Name": model_name,
                "Version": version,
                "Environment": environment,
                "Error": error,
                "Failed At": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        )
        
    async def send_drift_alert(
        self,
        model_name: str,
        drift_type: str,
        drift_score: float,
        severity: str,
        affected_features: List[str]
    ):
        """Send data/target drift alert"""
        feature_text = ", ".join(affected_features[:5])
        if len(affected_features) > 5:
            feature_text += f" (+{len(affected_features) - 5} more)"
            
        await self.send_notification(
            message=f"Drift detected in model {model_name}.\n\nType: {drift_type}\nScore: {drift_score:.3f}\nAffected Features: {feature_text}",
            title="🚨 Model Drift Alert",
            severity=severity,
            metadata={
                "Model Name": model_name,
                "Drift Type": drift_type,
                "Drift Score": f"{drift_score:.3f}",
                "Severity": severity,
                "Affected Features": len(affected_features),
                "Detected At": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        )
        
    async def send_performance_degradation_alert(
        self,
        model_name: str,
        metric_name: str,
        current_value: float,
        previous_value: float,
        threshold: float
    ):
        """Send performance degradation alert"""
        degradation = ((previous_value - current_value) / previous_value) * 100
        
        await self.send_notification(
            message=f"Performance degradation detected in model {model_name}.\n\n{metric_name}: {current_value:.3f} (was {previous_value:.3f})\nDegradation: {degradation:.1f}%",
            title="⚠️ Performance Degradation Alert",
            severity="warning",
            metadata={
                "Model Name": model_name,
                "Metric": metric_name,
                "Current Value": f"{current_value:.3f}",
                "Previous Value": f"{previous_value:.3f}",
                "Degradation": f"{degradation:.1f}%",
                "Threshold": f"{threshold:.3f}",
                "Detected At": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        )
        
    async def send_training_completion(
        self,
        model_name: str,
        experiment_id: str,
        run_id: str,
        metrics: Dict[str, float]
    ):
        """Send model training completion notification"""
        metrics_text = "\n".join([f"  {k}: {v:.4f}" for k, v in metrics.items()])
        
        await self.send_notification(
            message=f"Model training completed for {model_name}.\n\nExperiment ID: {experiment_id}\nRun ID: {run_id}\n\nMetrics:\n{metrics_text}",
            title="✅ Training Complete",
            severity="success",
            metadata={
                "Model Name": model_name,
                "Experiment ID": experiment_id,
                "Run ID": run_id,
                **{f"Metric_{k}": f"{v:.4f}" for k, v in metrics.items()},
                "Completed At": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
        )