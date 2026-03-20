"""
Audit log module.

M-04 FIX: Provides structured security event logging.
All security-relevant actions are recorded through this module
for compliance, forensics, and anomaly detection.

Uses a dedicated 'audit' logger separate from application logs,
so audit events can be routed to a separate destination (e.g.,
SIEM, S3 bucket, or dedicated log file).
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AuditAction(str, Enum):
    """Security-relevant actions that are logged."""

    USER_REGISTER = "user.register"
    USER_LOGIN = "user.login"
    USER_LOGIN_FAILED = "user.login_failed"
    USER_LOGOUT = "user.logout"
    USER_PASSWORD_CHANGE = "user.password_change"
    USER_LOCKED_OUT = "user.locked_out"
    VIDEO_UPLOAD = "video.upload"
    VIDEO_DELETE = "video.delete"
    JOB_START = "job.start"
    JOB_CANCEL = "job.cancel"
    JOB_COMPLETE = "job.complete"
    JOB_FAIL = "job.fail"


# Dedicated audit logger — separate from application logs
_audit_logger = logging.getLogger("audit")


def audit(
    action: AuditAction,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    detail: Optional[dict] = None,
) -> None:
    """Record a security-relevant event to the audit log.

    Format: who, did what, to what resource, when, from where.

    Args:
        action: The action being performed.
        user_id: The user performing the action (if known).
        resource_id: The target resource ID (video, job, etc.).
        resource_type: The type of resource (video, job, user).
        ip_address: The client's IP address.
        success: Whether the action succeeded.
        detail: Additional context (truncated user_agent, file size, etc.).
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action.value,
        "user_id": user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip_address": ip_address,
        "success": success,
    }
    if detail:
        entry.update(detail)

    _audit_logger.info(json.dumps(entry, default=str))
