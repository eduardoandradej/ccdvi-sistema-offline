import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent

# Campos que nunca devem aparecer na trilha
_SECRET_KEYS = {"password", "password_hash", "token", "token_hash"}


def _jsonable(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if k not in _SECRET_KEYS}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def diff(before: dict, after: dict) -> dict:
    """Retorna somente os campos alterados no formato {campo: [antes, depois]}."""
    keys = set(before) | set(after)
    return {
        k: [_jsonable(before.get(k)), _jsonable(after.get(k))]
        for k in sorted(keys)
        if k not in _SECRET_KEYS and before.get(k) != after.get(k)
    }


def record(
    db: Session,
    action: str,
    *,
    ctx=None,
    user=None,
    object_type: str | None = None,
    object_id: Any = None,
    details: dict | None = None,
    outcome: str = "SUCESSO",
    client_ip: str | None = None,
) -> None:
    """Adiciona um evento de auditoria à transação corrente (o chamador faz commit)."""
    u = ctx.user if ctx is not None else user
    db.add(
        AuditEvent(
            user_id=u.id if u is not None else None,
            username=u.username if u is not None else None,
            operation_id=getattr(ctx, "operation_id", None),
            base_id=getattr(ctx, "base_id", None),
            role=getattr(ctx, "role", None),
            action=action,
            object_type=object_type,
            object_id=str(object_id) if object_id is not None else None,
            outcome=outcome,
            details=_jsonable(details or {}),
            client_ip=client_ip if client_ip is not None else getattr(ctx, "client_ip", None),
        )
    )
