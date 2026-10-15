import time
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import Ctx, _client_ip, get_session_ctx
from app.models import Authorization, OperationalBase, User, UserSession
from app.rbac import ROLES, permissions_for
from app.schemas import AuthorizationOut, BaseOut, ContextIn, LoginIn, MeOut, OperationOut
from app.security import new_session_token, token_digest, verify_password
from app.services import audit

router = APIRouter(prefix="/api/auth", tags=["autenticação e contexto"])

# Limitação simples de tentativas por usuário+IP (memória do processo)
_FAILS: dict[str, deque[float]] = defaultdict(deque)
MAX_FAILS, WINDOW_S = 5, 15 * 60


def _throttled(key: str) -> bool:
    q = _FAILS[key]
    now = time.monotonic()
    while q and now - q[0] > WINDOW_S:
        q.popleft()
    return len(q) >= MAX_FAILS


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    settings = get_settings()
    ip = _client_ip(request)
    key = f"{body.username.lower()}|{ip}"
    if _throttled(key):
        audit.record(db, "LOGIN", object_type="user", details={"username": body.username},
                     outcome="BLOQUEADO", client_ip=ip)
        db.commit()
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Muitas tentativas. Aguarde alguns minutos.")
    user = db.scalar(select(User).where(User.username == body.username))
    if not verify_password(user.password_hash if user else None, body.password) or not user.active:
        _FAILS[key].append(time.monotonic())
        audit.record(db, "LOGIN", object_type="user", details={"username": body.username},
                     outcome="FALHA", client_ip=ip)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário ou senha inválidos.")
    _FAILS.pop(key, None)
    token = new_session_token()
    sess = UserSession(
        token_hash=token_digest(token),
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(hours=settings.session_hours),
    )
    db.add(sess)
    audit.record(db, "LOGIN", user=user, object_type="user", object_id=user.id, client_ip=ip)
    db.commit()
    response.set_cookie(
        settings.cookie_name, token, httponly=True, samesite="strict",
        secure=settings.cookie_secure, max_age=settings.session_hours * 3600, path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response, ctx: Ctx = Depends(get_session_ctx), db: Session = Depends(get_db)):
    ctx.session.revoked = True
    db.add(ctx.session)
    audit.record(db, "LOGOUT", ctx=ctx, object_type="user", object_id=ctx.user.id)
    db.commit()
    response.delete_cookie(get_settings().cookie_name, path="/")
    return {"ok": True}


def _authorizations(db: Session, user: User) -> list[Authorization]:
    return list(
        db.scalars(
            select(Authorization).where(Authorization.user_id == user.id, Authorization.active.is_(True))
        )
    )


@router.get("/me", response_model=MeOut)
def me(ctx: Ctx = Depends(get_session_ctx), db: Session = Depends(get_db)):
    auths = [
        AuthorizationOut(
            operation=OperationOut.model_validate(a.operation),
            base=BaseOut.model_validate(a.base),
            role=a.role,
            role_label=ROLES.get(a.role, a.role),
        )
        for a in _authorizations(db, ctx.user)
        if a.operation.status == "ATIVA"
    ]
    context = None
    if ctx.operation_id:
        op = next(a.operation for a in auths if a.operation.id == ctx.operation_id)
        base = db.get(OperationalBase, ctx.base_id)
        context = {
            "operation": op.model_dump(mode="json"),
            "base": BaseOut.model_validate(base).model_dump(mode="json"),
            "role": ctx.role,
            "role_label": ROLES.get(ctx.role, ctx.role),
        }
    return MeOut(
        id=ctx.user.id, username=ctx.user.username, full_name=ctx.user.full_name,
        job_title=ctx.user.job_title, authorizations=auths, context=context,
        permissions=sorted(ctx.permissions),
    )


@router.put("/context")
def set_context(body: ContextIn, ctx: Ctx = Depends(get_session_ctx), db: Session = Depends(get_db)):
    """Troca de contexto: validada no servidor contra as autorizações da conta e auditada."""
    auth = db.scalar(
        select(Authorization).where(
            Authorization.user_id == ctx.user.id,
            Authorization.operation_id == body.operation_id,
            Authorization.base_id == body.base_id,
            Authorization.role == body.role,
            Authorization.active.is_(True),
        )
    )
    if auth is None or auth.operation.status != "ATIVA":
        audit.record(db, "TROCA_CONTEXTO", ctx=ctx, object_type="session", object_id=ctx.session.id,
                     details=body.model_dump(mode="json"), outcome="NEGADO")
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Contexto não autorizado para esta conta.")
    before = {"operation_id": ctx.session.operation_id, "base_id": ctx.session.base_id,
              "role": ctx.session.role}
    ctx.session.operation_id, ctx.session.base_id, ctx.session.role = (
        body.operation_id, body.base_id, body.role)
    db.add(ctx.session)
    ctx.operation_id, ctx.base_id, ctx.role = body.operation_id, body.base_id, body.role
    audit.record(db, "TROCA_CONTEXTO", ctx=ctx, object_type="session", object_id=ctx.session.id,
                 details={"antes": before, "depois": body.model_dump(mode="json")})
    db.commit()
    return {"ok": True, "permissions": sorted(permissions_for(body.role))}


@router.delete("/context")
def clear_context(ctx: Ctx = Depends(get_session_ctx), db: Session = Depends(get_db)):
    ctx.session.operation_id = ctx.session.base_id = ctx.session.role = None
    db.add(ctx.session)
    audit.record(db, "LIMPA_CONTEXTO", ctx=ctx, object_type="session", object_id=ctx.session.id)
    db.commit()
    return {"ok": True}
