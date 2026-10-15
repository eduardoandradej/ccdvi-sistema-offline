"""Funções compartilhadas pelos módulos AM e PM."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import vocab
from app.deps import Ctx
from app.models import AmCase, AuditEvent, Effect, PhysicalMark
from app.schemas import EffectIn, MarkIn
from app.services import audit


def get_case(db: Session, ctx: Ctx, model, case_id: uuid.UUID):
    """Carrega um caso somente se pertencer à operação ativa (isolamento por operação)."""
    case = db.get(model, case_id)
    if case is None or case.operation_id != ctx.operation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro não encontrado nesta operação.")
    return case


def snapshot(obj, fields: list[str]) -> dict:
    return {f: getattr(obj, f) for f in fields}


def check_certainty(kind: str, value: str) -> None:
    allowed = vocab.CERTAINTY_AM if kind == "AM" else vocab.CERTAINTY_PM
    if value not in allowed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Grau de certeza '{value}' não se aplica a registros {kind}. "
            f"Use: {', '.join(allowed)}.",
        )


def _owner_kwargs(case) -> dict:
    return {"am_case_id": case.id} if isinstance(case, AmCase) else {"pm_case_id": case.id}


def _owner_id(item) -> uuid.UUID | None:
    return item.am_case_id or item.pm_case_id


def _kind(case) -> str:
    return "AM" if isinstance(case, AmCase) else "PM"


def touch(case, ctx: Ctx) -> None:
    case.updated_by = ctx.user.id
    case.version += 1


def add_mark(db: Session, ctx: Ctx, case, body: MarkIn) -> PhysicalMark:
    check_certainty(_kind(case), body.certainty)
    mark = PhysicalMark(**body.model_dump(), **_owner_kwargs(case))
    db.add(mark)
    touch(case, ctx)
    db.flush()
    audit.record(db, f"{_kind(case)}_SINAL_INCLUIDO", ctx=ctx, object_type=f"{_kind(case).lower()}_case",
                 object_id=case.id, details={"sinal_id": mark.id, **body.model_dump()})
    return mark


def remove_mark(db: Session, ctx: Ctx, case, mark_id: uuid.UUID) -> None:
    mark = db.get(PhysicalMark, mark_id)
    if mark is None or _owner_id(mark) != case.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sinal não encontrado neste registro.")
    before = snapshot(mark, ["mark_type", "region", "description", "certainty", "source"])
    db.delete(mark)
    touch(case, ctx)
    audit.record(db, f"{_kind(case)}_SINAL_REMOVIDO", ctx=ctx, object_type=f"{_kind(case).lower()}_case",
                 object_id=case.id, details={"sinal_id": mark_id, "antes": before})


def add_effect(db: Session, ctx: Ctx, case, body: EffectIn) -> Effect:
    check_certainty(_kind(case), body.certainty)
    eff = Effect(**body.model_dump(), **_owner_kwargs(case))
    db.add(eff)
    touch(case, ctx)
    db.flush()
    audit.record(db, f"{_kind(case)}_ITEM_INCLUIDO", ctx=ctx, object_type=f"{_kind(case).lower()}_case",
                 object_id=case.id, details={"item_id": eff.id, **body.model_dump()})
    return eff


def remove_effect(db: Session, ctx: Ctx, case, effect_id: uuid.UUID) -> None:
    eff = db.get(Effect, effect_id)
    if eff is None or _owner_id(eff) != case.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado neste registro.")
    before = {c: getattr(eff, c) for c in EffectIn.model_fields}
    db.delete(eff)
    touch(case, ctx)
    audit.record(db, f"{_kind(case)}_ITEM_REMOVIDO", ctx=ctx, object_type=f"{_kind(case).lower()}_case",
                 object_id=case.id, details={"item_id": effect_id, "antes": before})


def history(db: Session, object_ids: list[str]) -> list[dict]:
    rows = db.scalars(
        select(AuditEvent).where(AuditEvent.object_id.in_(object_ids)).order_by(AuditEvent.id.desc())
    )
    return [
        {
            "id": r.id, "occurred_at": r.occurred_at, "username": r.username, "role": r.role,
            "action": r.action, "outcome": r.outcome, "details": r.details,
        }
        for r in rows
    ]


def version_conflict() -> HTTPException:
    return HTTPException(
        status.HTTP_409_CONFLICT,
        "O registro foi alterado por outra pessoa desde que foi aberto. Recarregue antes de salvar.",
    )

