"""Dependências de autenticação, contexto e autorização (verificadas em TODA requisição)."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Authorization, User, UserSession
from app.rbac import permissions_for
from app.security import token_digest

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_HEADER = "x-dvi-request"


@dataclass
class Ctx:
    user: User
    session: UserSession
    operation_id: uuid.UUID | None = None
    base_id: uuid.UUID | None = None
    role: str | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)
    client_ip: str | None = None

    def has(self, perm: str) -> bool:
        return perm in self.permissions


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def get_session_ctx(request: Request, db: Session = Depends(get_db)) -> Ctx:
    # Proteção CSRF: além do cookie SameSite=Strict, toda requisição de escrita precisa
    # de um cabeçalho customizado, que formulários de outros sites não conseguem enviar.
    if request.method in UNSAFE_METHODS and request.headers.get(CSRF_HEADER) != "1":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cabeçalho de requisição ausente.")
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado.")
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == token_digest(token)))
    now = datetime.now(UTC)
    if sess is None or sess.revoked or sess.expires_at <= now or not sess.user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")
    ctx = Ctx(user=sess.user, session=sess, client_ip=_client_ip(request))
    if sess.operation_id and sess.base_id and sess.role:
        # Revalida a autorização a cada requisição: revogar acesso tem efeito imediato.
        auth = db.scalar(
            select(Authorization).where(
                Authorization.user_id == sess.user_id,
                Authorization.operation_id == sess.operation_id,
                Authorization.base_id == sess.base_id,
                Authorization.role == sess.role,
                Authorization.active.is_(True),
            )
        )
        if auth is not None and auth.operation.status == "ATIVA":
            ctx.operation_id = sess.operation_id
            ctx.base_id = sess.base_id
            ctx.role = sess.role
            ctx.permissions = permissions_for(sess.role)
    return ctx


def get_ctx(ctx: Ctx = Depends(get_session_ctx)) -> Ctx:
    """Exige contexto operacional (operação + base + função) válido."""
    if ctx.operation_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Selecione operação, base e função.")
    return ctx


def require(*perms: str):
    def dep(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        missing = [p for p in perms if not ctx.has(p)]
        if missing:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente para esta ação.")
        return ctx

    return dep
