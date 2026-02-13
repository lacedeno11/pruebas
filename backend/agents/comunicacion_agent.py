"""Communication agent for sending notifications via Telegram and email."""

from backend.graph.state import PEIState, add_message
from backend.database.models import AgentLog
from backend.database.db import SessionLocal
from datetime import datetime
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Try to import notification providers
try:
    from telegram import Bot
    from telegram.error import TelegramError
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

try:
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    HAS_SMTP = True
except ImportError:
    HAS_SMTP = False

try:
    from langchain_openai import ChatOpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


EMAIL_TEMPLATE_OT_ASSIGNMENT = """
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1e88e5; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ margin: 20px 0; }}
        .footer {{ color: #999; font-size: 12px; margin-top: 20px; }}
        .ot-details {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>✅ Nueva Asignación de OT</h2>
        </div>
        <div class="content">
            <p>Hola,</p>
            <p>Se ha asignado una nueva orden de trabajo a tu cuadrilla:</p>
            <div class="ot-details">
                <p><strong>OT ID:</strong> {ot_id}</p>
                <p><strong>Cliente:</strong> {cliente_id}</p>
                <p><strong>Tipo de Proyecto:</strong> {project_type}</p>
                <p><strong>Ubicación:</strong> ({lat}, {long})</p>
                <p><strong>Cuadrilla:</strong> {cuadrilla_name}</p>
            </div>
            <p>Por favor, revisa los detalles y comienza el trabajo tan pronto como sea posible.</p>
        </div>
        <div class="footer">
            <p>PEI Agéntico Platform | Automated Work Order Management</p>
        </div>
    </div>
</body>
</html>
"""

EMAIL_TEMPLATE_GOVERNANCE_ALERT = """
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #ff9800; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ margin: 20px 0; }}
        .footer {{ color: #999; font-size: 12px; margin-top: 20px; }}
        .alert-box {{ background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>⚠️ Alerta de Gobernanza</h2>
        </div>
        <div class="content">
            <p>Hola,</p>
            <p>Se ha detectado una orden de trabajo que requiere atención inmediata:</p>
            <div class="alert-box">
                <p><strong>OT ID:</strong> {ot_id}</p>
                <p><strong>Cliente:</strong> {cliente_id}</p>
                <p><strong>Estado Actual:</strong> {status}</p>
                <p><strong>Días en Estado:</strong> {days_in_status}</p>
                <p><strong>Alerta:</strong> {alert_message}</p>
            </div>
            <p>Por favor, toma las acciones necesarias para resolver esta situación.</p>
        </div>
        <div class="footer">
            <p>PEI Agéntico Platform | Automated Work Order Management</p>
        </div>
    </div>
</body>
</html>
"""

EMAIL_TEMPLATE_INGESTION_ERROR = """
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #e53935; color: white; padding: 20px; border-radius: 5px; }}
        .content {{ margin: 20px 0; }}
        .footer {{ color: #999; font-size: 12px; margin-top: 20px; }}
        .error-box {{ background: #ffebee; border-left: 4px solid #e53935; padding: 15px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 Error en Ingesta de OTs</h2>
        </div>
        <div class="content">
            <p>Hola,</p>
            <p>Se han detectado errores durante la ingesta de órdenes de trabajo:</p>
            <div class="error-box">
                <p><strong>Total OTs Procesadas:</strong> {total_fetched}</p>
                <p><strong>Insertadas Exitosamente:</strong> {inserted}</p>
                <p><strong>Duplicadas:</strong> {duplicates}</p>
                <p><strong>Errores Geográficos:</strong> {geo_errors}</p>
                <p><strong>Mensaje de Error:</strong> {error_message}</p>
            </div>
            <p>Por favor, revisa los detalles e investiga los OTs con errores geográficos.</p>
        </div>
        <div class="footer">
            <p>PEI Agéntico Platform | Automated Work Order Management</p>
        </div>
    </div>
</body>
</html>
"""


async def communication_node(state: PEIState) -> PEIState:
    """
    Communication node that sends notifications to users.
    
    This node:
    1. Parses state.agent_responses to determine notification type and recipients
    2. Sends Telegram notifications to configured chat IDs
    3. Sends HTML email notifications to appropriate recipients
    4. Uses LLM to generate professional message content
    5. Implements retry logic (max 3 attempts) for failed sends
    6. Logs all sent notifications to AgentLog
    
    Args:
        state: Current PEIState with agent responses containing notification data
    
    Returns:
        Updated PEIState with communication results logged
    """
    
    logger.info("Communication Agent starting")
    
    db = SessionLocal()
    communication_stats = {
        "telegram_sent": 0,
        "telegram_failed": 0,
        "email_sent": 0,
        "email_failed": 0,
        "errors": [],
    }
    
    try:
        # Parse agent responses to determine notifications needed
        agent_responses = state.get("agent_responses", [])
        
        if not agent_responses:
            logger.info("No agent responses to notify about")
            return state
        
        # Process each agent response
        for agent_response in agent_responses:
            agent_name = agent_response.get("agent_name", "Unknown")
            response_data = agent_response.get("response", {})
            
            logger.info(f"Processing notification from {agent_name}")
            
            try:
                # Route to appropriate notification handler based on agent
                if agent_name == "OTS Ingest Agent":
                    await _handle_ingestion_notifications(
                        response_data, db, communication_stats
                    )
                
                elif agent_name == "Planificación Agent":
                    await _handle_planning_notifications(
                        response_data, db, communication_stats
                    )
                
                elif agent_name == "Gobernanza Agent":
                    await _handle_governance_notifications(
                        response_data, db, communication_stats
                    )
                
                elif agent_name == "Router Agent":
                    # Router doesn't require notifications
                    pass
                
                else:
                    logger.warning(f"Unknown agent: {agent_name}")
            
            except Exception as e:
                logger.error(f"Error processing notification from {agent_name}: {str(e)}")
                communication_stats["errors"].append(f"{agent_name}: {str(e)}")
        
        # Log communication summary
        try:
            total_sent = communication_stats["telegram_sent"] + communication_stats["email_sent"]
            total_failed = communication_stats["telegram_failed"] + communication_stats["email_failed"]
            
            agent_log = AgentLog(
                agente_name="Comunicación Agent",
                accion="Send Notifications",
                resultado=f"Telegram sent: {communication_stats['telegram_sent']}, Email sent: {communication_stats['email_sent']}, Failed: {total_failed}",
                timestamp=datetime.utcnow(),
            )
            db.add(agent_log)
            db.commit()
            logger.info(f"Communication summary: {total_sent} notifications sent, {total_failed} failed")
        
        except Exception as e:
            logger.error(f"Failed to log communication summary: {str(e)}")
        
        logger.info("Communication Agent completed")
        return state
    
    except Exception as e:
        logger.error(f"Communication Agent error: {str(e)}")
        state["error"] = f"Communication failed: {str(e)}"
        
        # Log error
        agent_log = AgentLog(
            agente_name="Comunicación Agent",
            accion="Send Notifications",
            resultado=f"ERROR: {str(e)}",
            timestamp=datetime.utcnow(),
        )
        db.add(agent_log)
        db.commit()
        
        return state
    
    finally:
        db.close()


async def _handle_ingestion_notifications(
    response_data: Dict[str, Any],
    db: SessionLocal,
    stats: Dict[str, int],
):
    """
    Handle notifications for OTS ingestion results.
    
    Args:
        response_data: Response from OTS Ingest Agent
        db: Database session
        stats: Communication statistics dict
    """
    total_fetched = response_data.get("total_fetched", 0)
    inserted = response_data.get("inserted", 0)
    geo_errors = response_data.get("geo_errors", 0)
    
    # Only send if there are errors
    if geo_errors == 0 and inserted > 0:
        logger.info("Ingestion successful with no errors, minimal notification")
        return
    
    # Send email to coordinator about geo errors
    if geo_errors > 0:
        try:
            message = f"""
            🚨 Se detectaron {geo_errors} OTs con errores geográficos durante la ingesta.
            
            Total procesados: {total_fetched}
            Insertados exitosamente: {inserted}
            Errores geográficos: {geo_errors}
            
            Por favor, revisa los OTs con coordenadas inválidas o fuera de Ecuador.
            """
            
            await _send_email(
                subject="⚠️ Errores de Ingesta de OTs",
                body=message,
                recipient="coordinator",
                html_template=EMAIL_TEMPLATE_INGESTION_ERROR,
                template_vars={
                    "total_fetched": total_fetched,
                    "inserted": inserted,
                    "duplicates": response_data.get("duplicates", 0),
                    "geo_errors": geo_errors,
                    "error_message": "Coordenadas geográficas inválidas o fuera de límites de Ecuador",
                },
            )
            stats["email_sent"] += 1
        except Exception as e:
            logger.error(f"Failed to send ingestion error email: {str(e)}")
            stats["email_failed"] += 1


async def _handle_planning_notifications(
    response_data: Dict[str, Any],
    db: SessionLocal,
    stats: Dict[str, int],
):
    """
    Handle notifications for planning results.
    
    Args:
        response_data: Response from Planificación Agent
        db: Database session
        stats: Communication statistics dict
    """
    phase1 = response_data.get("phase1_assignments", 0)
    phase2 = response_data.get("phase2_assignments", 0)
    pending = response_data.get("pending_manual", 0)
    
    # Send Telegram notification with planning summary
    try:
        message = f"""
        ✅ Planificación completada

        Fase 1 (Balance Inicial): {phase1} asignadas
        Fase 2 (Proximidad Centroide): {phase2} asignadas
        Pendientes de revisión manual: {pending}

        Total asignadas: {phase1 + phase2}
        """
        
        if pending > 0:
            message += f"\n\n⚠️ {pending} OTs requieren asignación manual (fuera del rango de 10km)"
        
        await _send_telegram_message(message, stats)
    
    except Exception as e:
        logger.error(f"Failed to send planning Telegram: {str(e)}")
        stats["telegram_failed"] += 1


async def _handle_governance_notifications(
    response_data: Dict[str, Any],
    db: SessionLocal,
    stats: Dict[str, int],
):
    """
    Handle notifications for governance alerts.
    
    Args:
        response_data: Response from Gobernanza Agent
        db: Database session
        stats: Communication statistics dict
    """
    check1_alerts = response_data.get("check1_alerts", 0)
    check2_cancellations = response_data.get("check2_cancellations", 0)
    total_actions = response_data.get("total_actions", 0)
    
    if total_actions == 0:
        logger.info("No governance actions required")
        return
    
    # Send Telegram alert about governance actions
    try:
        message = "🚨 Acciones de Gobernanza Ejecutadas\n\n"
        
        if check1_alerts > 0:
            message += f"⚠️ Alertas 48h (PREPLANIFICADA): {check1_alerts}\n"
        
        if check2_cancellations > 0:
            message += f"🚫 OTs Auto-canceladas (30 días DETENIDA): {check2_cancellations}\n"
        
        message += f"\nTotal de acciones: {total_actions}"
        
        await _send_telegram_message(message, stats)
    
    except Exception as e:
        logger.error(f"Failed to send governance Telegram: {str(e)}")
        stats["telegram_failed"] += 1


async def _send_telegram_message(
    message: str,
    stats: Dict[str, int],
    max_retries: int = 3,
) -> bool:
    """
    Send message via Telegram to configured chat IDs.
    
    Args:
        message: Message text to send (supports markdown)
        stats: Communication statistics dict to update
        max_retries: Maximum retry attempts
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not HAS_TELEGRAM:
        logger.warning("Telegram not available (python-telegram-bot not installed)")
        return False
    
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids_str = os.getenv("TELEGRAM_CHAT_IDS", "")
    
    if not telegram_token or not chat_ids_str:
        logger.warning("Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_IDS)")
        return False
    
    # Parse chat IDs
    chat_ids = [cid.strip() for cid in chat_ids_str.split(",") if cid.strip()]
    
    try:
        bot = Bot(token=telegram_token)
        
        for chat_id in chat_ids:
            for attempt in range(max_retries):
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown",
                    )
                    logger.info(f"Telegram message sent to {chat_id}")
                    stats["telegram_sent"] += 1
                    return True
                
                except TelegramError as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Failed to send Telegram message to {chat_id}: {str(e)}")
                        stats["telegram_failed"] += 1
                        return False
    
    except Exception as e:
        logger.error(f"Telegram error: {str(e)}")
        return False


async def _send_email(
    subject: str,
    body: str,
    recipient: str,
    html_template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> bool:
    """
    Send HTML email notification.
    
    Args:
        subject: Email subject
        body: Plain text body (used if html_template not provided)
        recipient: Recipient type ('coordinator', 'pm', 'technician')
        html_template: Optional HTML template
        template_vars: Variables for template rendering
        max_retries: Maximum retry attempts
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    if not HAS_SMTP:
        logger.warning("SMTP not available (aiosmtplib not installed)")
        return False
    
    # Get configuration
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not smtp_user or not smtp_password:
        logger.warning("SMTP not configured (missing SMTP_USER or SMTP_PASSWORD)")
        return False
    
    # Determine recipient email
    recipient_email = _get_recipient_email(recipient)
    if not recipient_email:
        logger.warning(f"Unknown recipient type: {recipient}")
        return False
    
    try:
        # Prepare email content
        if html_template and template_vars:
            html_body = html_template.format(**template_vars)
        else:
            html_body = f"<html><body><pre>{body}</pre></body></html>"
        
        # Create email message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = recipient_email
        
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        # Send with retries
        for attempt in range(max_retries):
            try:
                async with aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port) as smtp:
                    await smtp.login(smtp_user, smtp_password)
                    await smtp.sendmail(smtp_user, recipient_email, msg.as_string())
                
                logger.info(f"Email sent to {recipient_email}: {subject}")
                return True
            
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"Failed to send email after {max_retries} attempts: {str(e)}")
                    return False
    
    except Exception as e:
        logger.error(f"Email preparation error: {str(e)}")
        return False


def _get_recipient_email(recipient_type: str) -> Optional[str]:
    """
    Get recipient email based on type.
    
    Args:
        recipient_type: Type of recipient ('coordinator', 'pm', 'technician')
    
    Returns:
        Email address or None if not configured
    """
    email_mapping = {
        "coordinator": os.getenv("COORDINATOR_EMAIL"),
        "pm": os.getenv("PM_EMAIL"),
        "technician": os.getenv("TECHNICIAN_EMAIL"),
        "admin": os.getenv("ADMIN_EMAIL"),
    }
    
    return email_mapping.get(recipient_type.lower())


def get_communication_status(db_session=None) -> dict:
    """
    Get recent communication history.
    
    Args:
        db_session: Optional database session
    
    Returns:
        dict: Recent communications from AgentLog
    """
    if db_session is None:
        from backend.database.db import SessionLocal
        db_session = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    try:
        # Get recent communication logs
        recent_logs = (
            db_session.query(AgentLog)
            .filter(AgentLog.agente_name == "Comunicación Agent")
            .order_by(AgentLog.timestamp.desc())
            .limit(10)
            .all()
        )
        
        return {
            "recent_communications": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "accion": log.accion,
                    "resultado": log.resultado,
                }
                for log in recent_logs
            ]
        }
    finally:
        if close_db:
            db_session.close()

