"""
Notification Service

This module implements notification services for alerts, updates, and communication,
supporting multiple notification channels (email, Slack, SMS, etc.).
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.base import MimeBase
from email import encoders

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification channel types"""
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"
    TEAMS = "teams"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationConfig:
    """Notification service configuration"""
    # Email configuration
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: Optional[str] = None
    
    # Slack configuration
    slack_webhook_url: Optional[str] = None
    slack_bot_token: Optional[str] = None
    slack_channel: Optional[str] = None
    
    # SMS configuration
    sms_provider: Optional[str] = None
    sms_api_key: Optional[str] = None
    sms_from_number: Optional[str] = None
    
    # Webhook configuration
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    
    # General settings
    retry_attempts: int = 3
    retry_delay_seconds: int = 60
    rate_limit_per_minute: int = 60


@dataclass
class NotificationMessage:
    """Notification message structure"""
    id: str
    channel: NotificationChannel
    priority: NotificationPriority
    subject: str
    content: str
    recipients: List[str]
    attachments: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class NotificationResult:
    """Notification delivery result"""
    message_id: str
    channel: NotificationChannel
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    external_id: Optional[str] = None


class NotificationAdapter(ABC):
    """Abstract base class for notification adapters"""
    
    def __init__(self, channel: NotificationChannel, config: NotificationConfig):
        self.channel = channel
        self.config = config
        self.stats = {
            "sent": 0,
            "delivered": 0,
            "failed": 0,
            "retries": 0
        }
    
    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send notification through this channel"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check adapter health"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        stats = self.stats.copy()
        total = stats["sent"] + stats["failed"]
        if total > 0:
            stats["success_rate"] = stats["sent"] / total
            stats["failure_rate"] = stats["failed"] / total
        return stats


class EmailNotificationAdapter(NotificationAdapter):
    """
    Email notification adapter using SMTP.
    
    Supports HTML/text emails with attachments and delivery tracking.
    """
    
    def __init__(self, config: NotificationConfig):
        super().__init__(NotificationChannel.EMAIL, config)
        
        if not all([config.smtp_host, config.smtp_username, config.smtp_password, config.from_email]):
            raise ValueError("Email configuration incomplete: missing SMTP settings")
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send email notification"""
        try:
            logger.info(f"Sending email notification: {message.id}")
            
            # Create email message
            msg = MimeMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = self.config.from_email
            msg['To'] = ', '.join(message.recipients)
            
            # Add content (support both HTML and plain text)
            if message.content.startswith('<html>') or '<' in message.content:
                # HTML content
                html_part = MimeText(message.content, 'html')
                msg.attach(html_part)
                
                # Also add plain text version
                import html2text
                text_content = html2text.html2text(message.content)
                text_part = MimeText(text_content, 'plain')
                msg.attach(text_part)
            else:
                # Plain text content
                text_part = MimeText(message.content, 'plain')
                msg.attach(text_part)
            
            # Add attachments if any
            if message.attachments:
                for attachment in message.attachments:
                    await self._add_attachment(msg, attachment)
            
            # Send email
            await self._send_smtp_email(msg, message.recipients)
            
            # Update statistics
            self.stats["sent"] += 1
            
            return NotificationResult(
                message_id=message.id,
                channel=self.channel,
                status=NotificationStatus.SENT,
                sent_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            self.stats["failed"] += 1
            
            return NotificationResult(
                message_id=message.id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    async def _send_smtp_email(self, msg: MimeMultipart, recipients: List[str]) -> None:
        """Send email via SMTP"""
        
        def send_email():
            server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
            
            if self.config.smtp_use_tls:
                server.starttls()
            
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.send_message(msg, to_addrs=recipients)
            server.quit()
        
        # Run SMTP operation in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, send_email)
    
    async def _add_attachment(self, msg: MimeMultipart, attachment: Dict[str, Any]) -> None:
        """Add attachment to email"""
        try:
            filename = attachment.get('filename', 'attachment')
            content = attachment.get('content', b'')
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            part = MimeBase('application', 'octet-stream')
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}'
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add email attachment: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check email service health"""
        try:
            # Test SMTP connection
            def test_connection():
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                if self.config.smtp_use_tls:
                    server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.quit()
                return True
            
            await asyncio.get_event_loop().run_in_executor(None, test_connection)
            
            return {
                "status": "healthy",
                "channel": "email",
                "smtp_host": self.config.smtp_host,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "channel": "email",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


class SlackNotificationAdapter(NotificationAdapter):
    """
    Slack notification adapter using webhooks or bot API.
    
    Supports rich formatting, mentions, and channel targeting.
    """
    
    def __init__(self, config: NotificationConfig):
        super().__init__(NotificationChannel.SLACK, config)
        
        if not (config.slack_webhook_url or config.slack_bot_token):
            raise ValueError("Slack configuration incomplete: missing webhook URL or bot token")
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send Slack notification"""
        try:
            logger.info(f"Sending Slack notification: {message.id}")
            
            # Prepare Slack message
            slack_message = await self._prepare_slack_message(message)
            
            # Send via webhook or API
            if self.config.slack_webhook_url:
                result = await self._send_webhook_message(slack_message)
            else:
                result = await self._send_api_message(slack_message, message.recipients)
            
            self.stats["sent"] += 1
            
            return NotificationResult(
                message_id=message.id,
                channel=self.channel,
                status=NotificationStatus.SENT,
                sent_at=datetime.utcnow(),
                external_id=result.get("ts")  # Slack timestamp
            )
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            self.stats["failed"] += 1
            
            return NotificationResult(
                message_id=message.id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    async def _prepare_slack_message(self, message: NotificationMessage) -> Dict[str, Any]:
        """Prepare Slack message format"""
        
        # Map priority to color
        color_map = {
            NotificationPriority.LOW: "#36a64f",      # Green
            NotificationPriority.NORMAL: "#2196F3",   # Blue
            NotificationPriority.HIGH: "#ff9800",     # Orange
            NotificationPriority.CRITICAL: "#f44336"  # Red
        }
        
        # Create rich message with attachments
        slack_message = {
            "text": message.subject,
            "attachments": [
                {
                    "color": color_map.get(message.priority, "#2196F3"),
                    "fields": [
                        {
                            "title": "Priority",
                            "value": message.priority.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Message ID",
                            "value": message.id,
                            "short": True
                        }
                    ],
                    "text": message.content,
                    "footer": "Policy Copilot",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        # Add metadata fields if present
        if message.metadata:
            for key, value in message.metadata.items():
                slack_message["attachments"][0]["fields"].append({
                    "title": key.replace("_", " ").title(),
                    "value": str(value),
                    "short": True
                })
        
        return slack_message
    
    async def _send_webhook_message(self, slack_message: Dict[str, Any]) -> Dict[str, Any]:
        """Send message via Slack webhook"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.config.slack_webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    raise Exception(f"Slack webhook failed: {response.status}")
                
                return {"status": "sent"}
    
    async def _send_api_message(self, slack_message: Dict[str, Any], recipients: List[str]) -> Dict[str, Any]:
        """Send message via Slack API"""
        import aiohttp
        
        # Use first recipient as channel (or default channel)
        channel = recipients[0] if recipients else self.config.slack_channel
        
        api_message = {
            "channel": channel,
            "text": slack_message["text"],
            "attachments": slack_message["attachments"]
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.slack_bot_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://slack.com/api/chat.postMessage",
                json=api_message,
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Slack API failed: {response.status}")
                
                result = await response.json()
                if not result.get("ok"):
                    raise Exception(f"Slack API error: {result.get('error')}")
                
                return result
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Slack service health"""
        try:
            if self.config.slack_webhook_url:
                # Test webhook with a simple message
                test_message = {"text": "Health check"}
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.config.slack_webhook_url,
                        json=test_message,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status != 200:
                            raise Exception(f"Webhook test failed: {response.status}")
            
            elif self.config.slack_bot_token:
                # Test API with auth.test
                headers = {"Authorization": f"Bearer {self.config.slack_bot_token}"}
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://slack.com/api/auth.test",
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status != 200:
                            raise Exception(f"API test failed: {response.status}")
                        
                        result = await response.json()
                        if not result.get("ok"):
                            raise Exception(f"API auth failed: {result.get('error')}")
            
            return {
                "status": "healthy",
                "channel": "slack",
                "method": "webhook" if self.config.slack_webhook_url else "api",
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "channel": "slack",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


class SMSNotificationAdapter(NotificationAdapter):
    """
    SMS notification adapter supporting multiple providers.
    
    Supports Twilio, AWS SNS, and other SMS providers.
    """
    
    def __init__(self, config: NotificationConfig):
        super().__init__(NotificationChannel.SMS, config)
        
        if not all([config.sms_provider, config.sms_api_key, config.sms_from_number]):
            raise ValueError("SMS configuration incomplete: missing provider settings")
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send SMS notification"""
        try:
            logger.info(f"Sending SMS notification: {message.id}")
            
            # Prepare SMS content (limit to 160 characters for standard SMS)
            sms_content = self._prepare_sms_content(message)
            
            # Send via configured provider
            if self.config.sms_provider.lower() == "twilio":
                result = await self._send_twilio_sms(sms_content, message.recipients)
            elif self.config.sms_provider.lower() == "aws_sns":
                result = await self._send_aws_sns_sms(sms_content, message.recipients)
            else:
                raise ValueError(f"Unsupported SMS provider: {self.config.sms_provider}")
            
            self.stats["sent"] += 1
            
            return NotificationResult(
                message_id=message.id,
                channel=self.channel,
                status=NotificationStatus.SENT,
                sent_at=datetime.utcnow(),
                external_id=result.get("sid")
            )
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            self.stats["failed"] += 1
            
            return NotificationResult(
                message_id=message.id,
                channel=self.channel,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
    
    def _prepare_sms_content(self, message: NotificationMessage) -> str:
        """Prepare SMS content with length limits"""
        
        # Combine subject and content
        full_content = f"{message.subject}: {message.content}"
        
        # Truncate if too long (leave space for sender info)
        max_length = 140  # Leave some buffer
        if len(full_content) > max_length:
            full_content = full_content[:max_length-3] + "..."
        
        return full_content
    
    async def _send_twilio_sms(self, content: str, recipients: List[str]) -> Dict[str, Any]:
        """Send SMS via Twilio"""
        try:
            from twilio.rest import Client
            
            # Parse API key (format: account_sid:auth_token)
            account_sid, auth_token = self.config.sms_api_key.split(":", 1)
            
            client = Client(account_sid, auth_token)
            
            # Send to each recipient
            results = []
            for recipient in recipients:
                message = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.messages.create(
                        body=content,
                        from_=self.config.sms_from_number,
                        to=recipient
                    )
                )
                results.append({"sid": message.sid, "to": recipient})
            
            return {"results": results, "sid": results[0]["sid"] if results else None}
            
        except ImportError:
            raise Exception("Twilio library not installed. Install with: pip install twilio")
        except Exception as e:
            raise Exception(f"Twilio SMS failed: {e}")
    
    async def _send_aws_sns_sms(self, content: str, recipients: List[str]) -> Dict[str, Any]:
        """Send SMS via AWS SNS"""
        try:
            import boto3
            
            # Create SNS client
            sns = boto3.client('sns')
            
            # Send to each recipient
            results = []
            for recipient in recipients:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: sns.publish(
                        PhoneNumber=recipient,
                        Message=content
                    )
                )
                results.append({"message_id": response["MessageId"], "to": recipient})
            
            return {"results": results, "sid": results[0]["message_id"] if results else None}
            
        except ImportError:
            raise Exception("Boto3 library not installed. Install with: pip install boto3")
        except Exception as e:
            raise Exception(f"AWS SNS SMS failed: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check SMS service health"""
        try:
            if self.config.sms_provider.lower() == "twilio":
                # Test Twilio connection
                from twilio.rest import Client
                account_sid, auth_token = self.config.sms_api_key.split(":", 1)
                client = Client(account_sid, auth_token)
                
                # Get account info to test connection
                account = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: client.api.accounts(account_sid).fetch()
                )
                
                return {
                    "status": "healthy",
                    "channel": "sms",
                    "provider": "twilio",
                    "account_sid": account_sid,
                    "last_check": datetime.utcnow().isoformat()
                }
            
            elif self.config.sms_provider.lower() == "aws_sns":
                # Test AWS SNS connection
                import boto3
                sns = boto3.client('sns')
                
                # List topics to test connection
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: sns.list_topics()
                )
                
                return {
                    "status": "healthy",
                    "channel": "sms",
                    "provider": "aws_sns",
                    "last_check": datetime.utcnow().isoformat()
                }
            
            else:
                raise Exception(f"Unknown SMS provider: {self.config.sms_provider}")
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "channel": "sms",
                "provider": self.config.sms_provider,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


class NotificationService:
    """
    Main notification service orchestrating multiple channels.
    
    Provides unified interface for sending notifications across
    different channels with retry logic and delivery tracking.
    """
    
    def __init__(self, config: NotificationConfig):
        self.config = config
        self.adapters: Dict[NotificationChannel, NotificationAdapter] = {}
        self.message_queue: List[NotificationMessage] = []
        self.retry_queue: List[Dict[str, Any]] = []
        
        # Initialize adapters based on configuration
        self._initialize_adapters()
        
        # Statistics
        self.stats = {
            "total_sent": 0,
            "total_failed": 0,
            "by_channel": {},
            "by_priority": {}
        }
    
    def _initialize_adapters(self) -> None:
        """Initialize notification adapters based on configuration"""
        
        # Email adapter
        if all([self.config.smtp_host, self.config.smtp_username, self.config.smtp_password]):
            try:
                self.adapters[NotificationChannel.EMAIL] = EmailNotificationAdapter(self.config)
                logger.info("Email notification adapter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize email adapter: {e}")
        
        # Slack adapter
        if self.config.slack_webhook_url or self.config.slack_bot_token:
            try:
                self.adapters[NotificationChannel.SLACK] = SlackNotificationAdapter(self.config)
                logger.info("Slack notification adapter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Slack adapter: {e}")
        
        # SMS adapter
        if all([self.config.sms_provider, self.config.sms_api_key, self.config.sms_from_number]):
            try:
                self.adapters[NotificationChannel.SMS] = SMSNotificationAdapter(self.config)
                logger.info("SMS notification adapter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize SMS adapter: {e}")
    
    async def send_notification(self, message: NotificationMessage) -> NotificationResult:
        """Send notification through specified channel"""
        
        try:
            # Check if adapter is available
            adapter = self.adapters.get(message.channel)
            if not adapter:
                raise Exception(f"No adapter available for channel: {message.channel}")
            
            # Check if message is scheduled for future
            if message.scheduled_at and message.scheduled_at > datetime.utcnow():
                self.message_queue.append(message)
                return NotificationResult(
                    message_id=message.id,
                    channel=message.channel,
                    status=NotificationStatus.PENDING
                )
            
            # Check if message has expired
            if message.expires_at and message.expires_at < datetime.utcnow():
                return NotificationResult(
                    message_id=message.id,
                    channel=message.channel,
                    status=NotificationStatus.FAILED,
                    error_message="Message expired"
                )
            
            # Send notification
            result = await adapter.send_notification(message)
            
            # Update statistics
            self._update_stats(message, result)
            
            # Add to retry queue if failed
            if result.status == NotificationStatus.FAILED:
                await self._add_to_retry_queue(message, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Notification service error: {e}")
            
            result = NotificationResult(
                message_id=message.id,
                channel=message.channel,
                status=NotificationStatus.FAILED,
                error_message=str(e)
            )
            
            self._update_stats(message, result)
            await self._add_to_retry_queue(message, result)
            
            return result
    
    async def send_multi_channel_notification(
        self,
        subject: str,
        content: str,
        channels: List[NotificationChannel],
        recipients: Dict[NotificationChannel, List[str]],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[NotificationChannel, NotificationResult]:
        """Send notification across multiple channels"""
        
        results = {}
        
        for channel in channels:
            channel_recipients = recipients.get(channel, [])
            if not channel_recipients:
                continue
            
            message = NotificationMessage(
                id=f"{datetime.utcnow().timestamp()}_{channel.value}",
                channel=channel,
                priority=priority,
                subject=subject,
                content=content,
                recipients=channel_recipients,
                metadata=metadata
            )
            
            result = await self.send_notification(message)
            results[channel] = result
        
        return results
    
    async def process_scheduled_messages(self) -> None:
        """Process scheduled messages that are ready to send"""
        
        current_time = datetime.utcnow()
        messages_to_send = []
        
        # Find messages ready to send
        for message in self.message_queue:
            if message.scheduled_at and message.scheduled_at <= current_time:
                messages_to_send.append(message)
        
        # Remove from queue and send
        for message in messages_to_send:
            self.message_queue.remove(message)
            await self.send_notification(message)
    
    async def process_retry_queue(self) -> None:
        """Process failed messages for retry"""
        
        current_time = datetime.utcnow()
        items_to_retry = []
        
        # Find items ready for retry
        for item in self.retry_queue:
            if item["retry_at"] <= current_time:
                items_to_retry.append(item)
        
        # Remove from queue and retry
        for item in items_to_retry:
            self.retry_queue.remove(item)
            
            if item["retry_count"] < self.config.retry_attempts:
                message = item["message"]
                result = await self.send_notification(message)
                
                # Update retry count
                if result.status == NotificationStatus.FAILED:
                    await self._add_to_retry_queue(message, result, item["retry_count"] + 1)
    
    async def _add_to_retry_queue(
        self,
        message: NotificationMessage,
        result: NotificationResult,
        retry_count: int = 0
    ) -> None:
        """Add failed message to retry queue"""
        
        if retry_count >= self.config.retry_attempts:
            logger.error(f"Max retries exceeded for message: {message.id}")
            return
        
        retry_item = {
            "message": message,
            "result": result,
            "retry_count": retry_count,
            "retry_at": datetime.utcnow().timestamp() + self.config.retry_delay_seconds
        }
        
        self.retry_queue.append(retry_item)
        logger.info(f"Added message to retry queue: {message.id}, attempt {retry_count + 1}")
    
    def _update_stats(self, message: NotificationMessage, result: NotificationResult) -> None:
        """Update notification statistics"""
        
        if result.status == NotificationStatus.SENT:
            self.stats["total_sent"] += 1
        else:
            self.stats["total_failed"] += 1
        
        # By channel
        channel_key = message.channel.value
        if channel_key not in self.stats["by_channel"]:
            self.stats["by_channel"][channel_key] = {"sent": 0, "failed": 0}
        
        if result.status == NotificationStatus.SENT:
            self.stats["by_channel"][channel_key]["sent"] += 1
        else:
            self.stats["by_channel"][channel_key]["failed"] += 1
        
        # By priority
        priority_key = message.priority.value
        if priority_key not in self.stats["by_priority"]:
            self.stats["by_priority"][priority_key] = {"sent": 0, "failed": 0}
        
        if result.status == NotificationStatus.SENT:
            self.stats["by_priority"][priority_key]["sent"] += 1
        else:
            self.stats["by_priority"][priority_key]["failed"] += 1
    
    async def health_check_all_adapters(self) -> Dict[str, Any]:
        """Check health of all notification adapters"""
        
        health_results = {}
        
        for channel, adapter in self.adapters.items():
            health_results[channel.value] = await adapter.health_check()
        
        return {
            "overall_status": "healthy" if all(
                result["status"] == "healthy" 
                for result in health_results.values()
            ) else "degraded",
            "adapters": health_results,
            "last_check": datetime.utcnow().isoformat()
        }
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive notification statistics"""
        
        stats = self.stats.copy()
        
        # Add adapter stats
        stats["adapter_stats"] = {}
        for channel, adapter in self.adapters.items():
            stats["adapter_stats"][channel.value] = adapter.get_stats()
        
        # Add queue stats
        stats["queue_stats"] = {
            "scheduled_messages": len(self.message_queue),
            "retry_queue_size": len(self.retry_queue)
        }
        
        return stats


# Factory functions

def create_notification_service(config: NotificationConfig) -> NotificationService:
    """Create notification service with configuration"""
    return NotificationService(config)


def create_email_config(
    smtp_host: str,
    smtp_username: str,
    smtp_password: str,
    from_email: str,
    smtp_port: int = 587,
    smtp_use_tls: bool = True
) -> NotificationConfig:
    """Create email notification configuration"""
    return NotificationConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        smtp_use_tls=smtp_use_tls,
        from_email=from_email
    )


def create_slack_config(
    webhook_url: Optional[str] = None,
    bot_token: Optional[str] = None,
    channel: Optional[str] = None
) -> NotificationConfig:
    """Create Slack notification configuration"""
    return NotificationConfig(
        slack_webhook_url=webhook_url,
        slack_bot_token=bot_token,
        slack_channel=channel
    )


def create_sms_config(
    provider: str,
    api_key: str,
    from_number: str
) -> NotificationConfig:
    """Create SMS notification configuration"""
    return NotificationConfig(
        sms_provider=provider,
        sms_api_key=api_key,
        sms_from_number=from_number
    )
