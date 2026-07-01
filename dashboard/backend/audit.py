"""
NiftyQuant Audit Logging — records security-relevant events.
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session
from database import AuditLog

logger = logging.getLogger("audit")


def log_event(db: Session, user_id: int | None, action: str, detail: str | None, ip: str | None):
    """
    Write an audit log entry. Actions:
      LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT, ACCOUNT_LOCKED, ACCOUNT_CREATED,
      KITE_CONNECTED, KITE_DISCONNECTED, ORDER_PLACED, ORDER_CANCELLED
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            detail=detail,
            ip_address=ip,
            timestamp=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        db.rollback()
