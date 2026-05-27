"""Security event logging — append-only audit trail for guardrail actions.

Every guardrail that fires (block, flag, redact) records a SecurityEvent.
This module provides the async helper used by all guardrail components.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import SecurityEvent, SecurityEventKind

logger = logging.getLogger("rag.guardrails.events")


async def log_security_event(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    kind: SecurityEventKind,
    severity: str,
    source: str,
    description: str,
    document_id: UUID | None = None,
    trace_id: UUID | None = None,
    user_id: UUID | None = None,
    details: dict | None = None,
) -> SecurityEvent:
    """Create and flush a SecurityEvent row.

    The caller must still commit the enclosing transaction.
    """
    event = SecurityEvent(
        tenant_id=tenant_id,
        kind=kind,
        severity=severity,
        source=source,
        description=description,
        document_id=document_id,
        trace_id=trace_id,
        user_id=user_id,
        details=details or {},
    )
    db.add(event)
    await db.flush()

    logger.warning(
        "security_event kind=%s severity=%s source=%s tenant=%s doc=%s: %s",
        kind.value,
        severity,
        source,
        tenant_id,
        document_id,
        description,
    )
    return event
