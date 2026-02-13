from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from app.models import OT, LogAgente
from app.config import get_settings


class GovernanceService:
    """Service for governance rules and auto-cancellation logic"""

    def __init__(self):
        self.settings = get_settings()

    def check_detention_alerts(self, session: Session) -> List[OT]:
        """
        Check for OTs in DETENIDA status and send alerts for days 20, 25, 29
        """
        alert_days = self.settings.ALERT_DETENTION_DAYS
        alerted_ots = []
        
        detained_ots = session.query(OT).filter(
            OT.status == "DETENIDA"
        ).all()
        
        for ot in detained_ots:
            days_detained = (datetime.utcnow() - ot.created_at).days
            
            if days_detained in alert_days:
                alerted_ots.append(ot)
                # Log alert
                log = LogAgente(
                    ot_id=ot.id,
                    agente_name="GobernanzaAgent",
                    accion="check_detention_alerts",
                    resultado=f"Alert sent for {days_detained} days detention",
                )
                session.add(log)
        
        session.commit()
        return alerted_ots

    def auto_cancel_inactive(self, session: Session) -> int:
        """
        Auto-cancel OTs in DETENIDA for > AUTO_CANCEL_DAYS (30)
        """
        auto_cancel_days = self.settings.AUTO_CANCEL_DAYS
        cancelled_count = 0
        
        detention_threshold = datetime.utcnow() - timedelta(days=auto_cancel_days)
        
        detained_ots = session.query(OT).filter(
            OT.status == "DETENIDA",
            OT.created_at < detention_threshold
        ).all()
        
        for ot in detained_ots:
            ot.status = "ANULADA"
            cancelled_count += 1
            
            # Log auto-cancellation
            log = LogAgente(
                ot_id=ot.id,
                agente_name="GobernanzaAgent",
                accion="auto_cancel",
                accion_detalle="Anulación automática por inactividad",
                resultado="ANULADA",
            )
            session.add(log)
        
        session.commit()
        return cancelled_count

    def check_preplanned_timeout(self, session: Session) -> List[OT]:
        """
        Check for OTs in PREPLANIFICADA for > PREPLANNED_ALERT_HOURS (48)
        """
        alert_hours = self.settings.PREPLANNED_ALERT_HOURS
        timeout_ots = []
        
        timeout_threshold = datetime.utcnow() - timedelta(hours=alert_hours)
        
        preplanificada_ots = session.query(OT).filter(
            OT.status == "PREPLANIFICADA",
            OT.created_at < timeout_threshold
        ).all()
        
        for ot in preplanificada_ots:
            timeout_ots.append(ot)
            # Log high-priority alert
            hours_waiting = (datetime.utcnow() - ot.created_at).total_seconds() / 3600
            log = LogAgente(
                ot_id=ot.id,
                agente_name="GobernanzaAgent",
                accion="check_preplanned_timeout",
                resultado=f"High-priority alert: {hours_waiting:.1f} hours in PREPLANIFICADA",
            )
            session.add(log)
        
        session.commit()
        return timeout_ots

