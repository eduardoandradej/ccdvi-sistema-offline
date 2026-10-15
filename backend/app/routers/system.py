"""Vocabulários, saúde do serviço, painel do coordenador, auditoria e administração de usuários."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import vocab
from app.config import get_settings
from app.db import get_db
from app.deps import Ctx, get_session_ctx, require
from app.models import (
    AmCase,
    Attachment,
    AuditEvent,
    Authorization,
    MatchReview,
    OperationalBase,
    PmCase,
    User,
)
from app.rbac import ROLES
from app.security import hash_password, validate_password_policy
from app.services import audit, storage

router = APIRouter(prefix="/api", tags=["sistema"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Verificação pública mínima (sem dados): usada por Podman/systemd."""
    db.execute(text("select 1"))
    return {"status": "ok"}


@router.get("/vocab")
def get_vocab(_: Ctx = Depends(get_session_ctx)):
    return {**vocab.vocabularies(), "roles": ROLES}


@router.get("/admin/health")
def admin_health(ctx: Ctx = Depends(require("admin:health")), db: Session = Depends(get_db)):
    db_version = db.execute(text("select version()")).scalar()
    root = storage.storage_root()
    import shutil

    usage = shutil.disk_usage(root)
    return {
        "database": {"ok": True, "version": db_version},
        "storage": {"path": str(root), "free_bytes": usage.free, "total_bytes": usage.total},
        "max_upload_mb": get_settings().max_upload_mb,
    }


@router.get("/dashboard")
def dashboard(ctx: Ctx = Depends(require("dashboard:read")), db: Session = Depends(get_db)):
    """Somente contagens agregadas — sem nomes, fotos ou documentos."""
    op = ctx.operation_id

    def count_by(model, col):
        rows = db.execute(select(col, func.count()).where(model.operation_id == op).group_by(col))
        return {k: v for k, v in rows}

    return {
        "am_by_status": count_by(AmCase, AmCase.status),
        "pm_by_status": count_by(PmCase, PmCase.status),
        "attachments": db.scalar(select(func.count()).select_from(Attachment).where(Attachment.operation_id == op)),
        "reviews_by_status": count_by(MatchReview, MatchReview.status),
    }


@router.get("/audit")
def audit_list(action: str | None = None, username: str | None = None, object_id: str | None = None,
               since: datetime | None = None, limit: int = 200, ctx: Ctx = Depends(require("audit:read")),
               db: Session = Depends(get_db)):
    stmt = select(AuditEvent).where(
        (AuditEvent.operation_id == ctx.operation_id) | (AuditEvent.operation_id.is_(None)))
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    if username:
        stmt = stmt.where(AuditEvent.username == username)
    if object_id:
        stmt = stmt.where(AuditEvent.object_id == object_id)
    if since:
        stmt = stmt.where(AuditEvent.occurred_at >= since)
    rows = db.scalars(stmt.order_by(AuditEvent.id.desc()).limit(min(limit, 1000)))
    return [
        {"id": r.id, "occurred_at": r.occurred_at, "username": r.username, "role": r.role,
         "action": r.action, "object_type": r.object_type, "object_id": r.object_id,
         "outcome": r.outcome, "details": r.details, "client_ip": r.client_ip}
        for r in rows
    ]


# ---------------------------------------------------------------- administração de usuários


class UserCreate(BaseModel):
    username: str = Field(pattern=r"^[a-z0-9._-]{3,64}$")
    full_name: str = Field(min_length=3, max_length=200)
    job_title: str | None = Field(default=None, max_length=120)
    password: str = Field(min_length=10, max_length=256)


class GrantIn(BaseModel):
    user_id: uuid.UUID
    base_id: uuid.UUID
    role: str


@router.get("/admin/users")
def list_users(ctx: Ctx = Depends(require("admin:users")), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.username))
    out = []
    for u in users:
        auths = db.scalars(select(Authorization).where(Authorization.user_id == u.id,
                                                       Authorization.operation_id == ctx.operation_id))
        out.append({
            "id": u.id, "username": u.username, "full_name": u.full_name, "job_title": u.job_title,
            "active": u.active,
            "authorizations": [{"id": a.id, "base": a.base.name, "base_id": a.base_id, "role": a.role,
                                "active": a.active} for a in auths],
        })
    return out


@router.get("/admin/bases")
def list_bases(ctx: Ctx = Depends(require("admin:users")), db: Session = Depends(get_db)):
    return [{"id": b.id, "code": b.code, "name": b.name, "kind": b.kind}
            for b in db.scalars(select(OperationalBase).where(OperationalBase.operation_id == ctx.operation_id))]


@router.post("/admin/users", status_code=201)
def create_user(body: UserCreate, ctx: Ctx = Depends(require("admin:users")), db: Session = Depends(get_db)):
    try:
        validate_password_policy(body.password)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Nome de usuário já existe.")
    u = User(username=body.username, full_name=body.full_name, job_title=body.job_title,
             password_hash=hash_password(body.password))
    db.add(u)
    db.flush()
    audit.record(db, "USUARIO_CRIADO", ctx=ctx, object_type="user", object_id=u.id,
                 details={"username": u.username, "full_name": u.full_name})
    db.commit()
    return {"id": u.id}


@router.post("/admin/authorizations", status_code=201)
def grant(body: GrantIn, ctx: Ctx = Depends(require("admin:users")), db: Session = Depends(get_db)):
    if body.role not in ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Função inválida.")
    base = db.get(OperationalBase, body.base_id)
    if base is None or base.operation_id != ctx.operation_id or db.get(User, body.user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuário ou base não encontrados nesta operação.")
    if body.user_id == ctx.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Não é permitido conceder autorização a si mesmo.")
    auth = db.scalar(select(Authorization).where(
        Authorization.user_id == body.user_id, Authorization.operation_id == ctx.operation_id,
        Authorization.base_id == body.base_id, Authorization.role == body.role))
    if auth is None:
        auth = Authorization(user_id=body.user_id, operation_id=ctx.operation_id, base_id=body.base_id,
                             role=body.role)
        db.add(auth)
    auth.active = True
    db.flush()
    audit.record(db, "AUTORIZACAO_CONCEDIDA", ctx=ctx, object_type="authorization", object_id=auth.id,
                 details=body.model_dump(mode="json"))
    db.commit()
    return {"id": auth.id}


@router.post("/admin/authorizations/{auth_id}/revoke")
def revoke(auth_id: uuid.UUID, ctx: Ctx = Depends(require("admin:users")), db: Session = Depends(get_db)):
    auth = db.get(Authorization, auth_id)
    if auth is None or auth.operation_id != ctx.operation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Autorização não encontrada.")
    auth.active = False
    audit.record(db, "AUTORIZACAO_REVOGADA", ctx=ctx, object_type="authorization", object_id=auth.id)
    db.commit()
    return {"ok": True}
