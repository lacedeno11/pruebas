import json
import smtplib
from typing import Optional, List, Dict, Any
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session

from langchain_openai import ChatOpenAI

from app.agents.state import PEIState, add_message
from app.config import get_settings
from app.models import LogAgente
from app.database import SessionLocal


class ComunicacionAgent:
    """
    Comunicación (Communication) Agent for sending notifications to stakeholders
    
    Responsible for:
    - Routing notifications to appropriate channels (Telegram for technicians, Email for PMs/Clients)
    - Formatting messages using LLM for natural language communication
    - Sending Telegram messages via telegram.Bot
    - Sending emails via SMTP
    - Handling MOCK mode by logging instead of actually sending
    - Logging all notification delivery attempts
    """

    def __init__(self):
        """Initialize ComunicacionAgent with OpenAI LLM and notification settings"""
        self.settings = get_settings()
        
        # Initialize ChatOpenAI LLM for message formatting
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.2,  # Low temperature for consistent message formatting
            api_key=self.settings.OPENAI_API_KEY,
        )
        
        # Initialize Telegram bot if token provided
        self.telegram_bot = None
        if self.settings.TELEGRAM_BOT_TOKEN:
            try:
                from telegram import Bot
                self.telegram_bot = Bot(token=self.settings.TELEGRAM_BOT_TOKEN)
            except Exception as e:
                print(f"Error initializing Telegram bot: {str(e)}")

    def send_notifications(self, state: PEIState) -> PEIState:
        """
        Send notifications to stakeholders via appropriate channels
        
        Args:
            state: Current PEIState from LangGraph
        
        Returns:
            Updated PEIState with notification delivery status
        """
        notifications = state.get("notifications", [])
        db_session = state.get("db_session")
        
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            delivery_results = []
            failed_count = 0
            
            for notification in notifications:
                try:
                    # Determine recipient type and send via appropriate channel
                    recipient_type = notification.get("recipient_type", "").lower()
                    ot_id = notification.get("ot_id")
                    message = notification.get("message", "")
                    
                    # Format message using LLM
                    formatted_message = self._format_notification_message(notification)
                    
                    if recipient_type == "tecnico":
                        # Send via Telegram to technician
                        success = self._send_telegram_notification(
                            notification,
                            formatted_message,
                            db_session,
                        )
                    elif recipient_type in ["pm", "cliente", "project_manager", "client"]:
                        # Send via Email to PM or Client
                        success = self._send_email_notification(
                            notification,
                            formatted_message,
                            db_session,
                        )
                    else:
                        # Unknown recipient type - default to email
                        success = self._send_email_notification(
                            notification,
                            formatted_message,
                            db_session,
                        )
                    
                    if success:
                        delivery_results.append({
                            "ot_id": ot_id,
                            "type": notification.get("type"),
                            "recipient": recipient_type,
                            "status": "sent",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                    else:
                        failed_count += 1
                        delivery_results.append({
                            "ot_id": ot_id,
                            "type": notification.get("type"),
                            "recipient": recipient_type,
                            "status": "failed",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
                        
                except Exception as e:
                    # Log error but continue with next notification
                    error_msg = f"Error sending notification: {str(e)}"
                    print(error_msg)
                    failed_count += 1
                    
                    self._log_notification_attempt(
                        db_session,
                        ot_id=notification.get("ot_id"),
                        notification_type=notification.get("type"),
                        recipient_type=notification.get("recipient_type"),
                        success=False,
                        error_message=error_msg,
                    )
            
            # Update state with delivery results
            state["notification_delivery"] = {
                "total": len(notifications),
                "sent": len(delivery_results) - failed_count,
                "failed": failed_count,
                "results": delivery_results,
            }
            
            # Add summary message
            summary_msg = (
                f"Comunicación Agent: Sent {len(delivery_results) - failed_count}/{len(notifications)} "
                f"notifications. {failed_count} failed."
            )
            state = add_message(state, "agent", summary_msg)
            
            return state
            
        except Exception as e:
            # Log critical error
            error_msg = f"Critical error in Comunicación Agent: {str(e)}"
            print(error_msg)
            state = add_message(state, "agent", error_msg)
            state["notification_delivery"] = {
                "total": len(notifications),
                "sent": 0,
                "failed": len(notifications),
                "results": [],
            }
            
            self._log_notification_attempt(
                db_session,
                ot_id=None,
                notification_type="unknown",
                recipient_type="unknown",
                success=False,
                error_message=error_msg,
            )
            
            return state
            
        finally:
            if should_close:
                db_session.close()

    def _format_notification_message(self, notification: Dict[str, Any]) -> str:
        """
        Format notification message using LLM for natural language communication
        
        Args:
            notification: Notification dictionary with type, ot_id, message, etc.
        
        Returns:
            Formatted notification message
        """
        try:
            notification_type = notification.get("type", "")
            ot_external_id = notification.get("ot_external_id", "UNKNOWN")
            project_type = notification.get("project_type", "")
            priority = notification.get("priority", "normal")
            
            # Build context for LLM formatting
            context = f"""Format the following notification for professional communication:
Notification Type: {notification_type}
OT ID: {ot_external_id}
Priority: {priority}
Original Message: {notification.get('message', '')}

Create a professional, concise notification message (max 200 words).
Include the OT ID, what happened, and recommended action if applicable.
Be formal but friendly."""
            
            response = self.llm.invoke(context)
            return response.content.strip()
            
        except Exception as e:
            # Fallback to original message if LLM fails
            return notification.get("message", "Notification from PEI System")

    def _send_telegram_notification(
        self,
        notification: Dict[str, Any],
        formatted_message: str,
        db_session: Session,
    ) -> bool:
        """
        Send notification via Telegram to technician
        
        Args:
            notification: Notification dictionary
            formatted_message: Formatted message to send
            db_session: SQLAlchemy session for logging
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # In MOCK mode, just log the message
            if self.settings.SYSTEM_MODE == "MOCK":
                print(f"[MOCK] Telegram message to tecnico: {formatted_message}")
                self._log_notification_attempt(
                    db_session,
                    ot_id=notification.get("ot_id"),
                    notification_type=notification.get("type"),
                    recipient_type="tecnico",
                    success=True,
                    channel="telegram_mock",
                )
                return True
            
            # In production, send via Telegram Bot
            if not self.telegram_bot:
                raise Exception("Telegram bot not initialized")
            
            # Get chat ID from notification or use default
            chat_id = notification.get("chat_id")
            if not chat_id:
                # In production, would look up chat ID from database
                raise Exception("No chat ID provided for Telegram notification")
            
            # Send message via Telegram Bot
            import asyncio
            asyncio.run(self.telegram_bot.send_message(
                chat_id=chat_id,
                text=formatted_message,
                parse_mode="HTML",  # Allow HTML formatting
            ))
            
            self._log_notification_attempt(
                db_session,
                ot_id=notification.get("ot_id"),
                notification_type=notification.get("type"),
                recipient_type="tecnico",
                success=True,
                channel="telegram",
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Telegram error: {str(e)}"
            print(error_msg)
            
            self._log_notification_attempt(
                db_session,
                ot_id=notification.get("ot_id"),
                notification_type=notification.get("type"),
                recipient_type="tecnico",
                success=False,
                error_message=error_msg,
                channel="telegram",
            )
            
            return False

    def _send_email_notification(
        self,
        notification: Dict[str, Any],
        formatted_message: str,
        db_session: Session,
    ) -> bool:
        """
        Send notification via Email to PM or Client
        
        Args:
            notification: Notification dictionary
            formatted_message: Formatted message to send
            db_session: SQLAlchemy session for logging
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # In MOCK mode, just log the message
            if self.settings.SYSTEM_MODE == "MOCK":
                recipient_email = notification.get("recipient_email", "pm@example.com")
                print(f"[MOCK] Email to {recipient_email}: {formatted_message}")
                self._log_notification_attempt(
                    db_session,
                    ot_id=notification.get("ot_id"),
                    notification_type=notification.get("type"),
                    recipient_type=notification.get("recipient_type", "pm"),
                    success=True,
                    channel="email_mock",
                )
                return True
            
            # In production, send via SMTP
            recipient_email = notification.get("recipient_email")
            if not recipient_email:
                # In production, would look up email from database
                raise Exception("No recipient email provided")
            
            ot_external_id = notification.get("ot_external_id", "OT-UNKNOWN")
            notification_type = notification.get("type", "notification")
            
            # Build email subject
            subject = f"PEI Alert: {notification_type.replace('_', ' ').title()} for OT {ot_external_id}"
            
            # Send email via SMTP
            self.send_email(
                to=recipient_email,
                subject=subject,
                body=formatted_message,
            )
            
            self._log_notification_attempt(
                db_session,
                ot_id=notification.get("ot_id"),
                notification_type=notification.get("type"),
                recipient_type=notification.get("recipient_type", "pm"),
                success=True,
                channel="email",
            )
            
            return True
            
        except Exception as e:
            error_msg = f"Email error: {str(e)}"
            print(error_msg)
            
            self._log_notification_attempt(
                db_session,
                ot_id=notification.get("ot_id"),
                notification_type=notification.get("type"),
                recipient_type=notification.get("recipient_type", "pm"),
                success=False,
                error_message=error_msg,
                channel="email",
            )
            
            return False

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """
        Send email via SMTP
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.settings.EMAIL_FROM
            message["To"] = to
            
            # Attach HTML version
            html_body = f"""
            <html>
              <body>
                <h2>PEI - Plataforma de Ejecución de Instalaciones</h2>
                {body.replace(chr(10), '<br>')}
                <hr>
                <p><small>This is an automated message from the PEI System.</small></p>
              </body>
            </html>
            """
            message.attach(MIMEText(html_body, "html"))
            
            # Send via SMTP
            with smtplib.SMTP(self.settings.EMAIL_SMTP_HOST, self.settings.EMAIL_SMTP_PORT) as server:
                server.starttls()
                # Add authentication if provided
                if hasattr(self.settings, 'EMAIL_SMTP_USER') and self.settings.EMAIL_SMTP_USER:
                    server.login(
                        self.settings.EMAIL_SMTP_USER,
                        self.settings.EMAIL_SMTP_PASSWORD or "",
                    )
                server.send_message(message)
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def send_telegram(self, chat_id: str, message: str) -> bool:
        """
        Send message via Telegram
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.telegram_bot:
                raise Exception("Telegram bot not initialized")
            
            import asyncio
            asyncio.run(self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
            ))
            
            return True
            
        except Exception as e:
            print(f"Error sending Telegram message: {str(e)}")
            return False

    def _log_notification_attempt(
        self,
        db_session: Optional[Session],
        ot_id: Optional[int],
        notification_type: str,
        recipient_type: str,
        success: bool,
        error_message: Optional[str] = None,
        channel: str = "unknown",
    ) -> None:
        """
        Log notification delivery attempt to LogAgente table for audit trail
        
        Args:
            db_session: SQLAlchemy session (optional)
            ot_id: OT database ID
            notification_type: Type of notification (detention_alert, preplanned_timeout, etc.)
            recipient_type: Recipient type (tecnico, pm, cliente)
            success: Whether sending was successful
            error_message: Optional error message
            channel: Delivery channel (telegram, email, etc.)
        """
        # If no session provided, create one temporarily
        if db_session is None:
            db_session = SessionLocal()
            should_close = True
        else:
            should_close = False
        
        try:
            log_entry = LogAgente(
                ot_id=ot_id,
                agente_name="ComunicacionAgent",
                accion="send_notification",
                resultado="ENVIADO" if success else "FALLO",
                raw_llm_response=json.dumps({
                    "notification_type": notification_type,
                    "recipient_type": recipient_type,
                    "channel": channel,
                    "success": success,
                    "error_message": error_message,
                }),
            )
            db_session.add(log_entry)
            db_session.commit()
        except Exception as e:
            # Log error but don't raise - notification delivery should proceed
            print(f"Error logging notification attempt: {str(e)}")
            db_session.rollback()
        finally:
            if should_close:
                db_session.close()

