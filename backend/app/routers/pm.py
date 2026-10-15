import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import Ctx, require
from app.models import Attachment, CustodyEvent, Operation, PmCase
from app.routers import common
from app.schemas import (
    CustodyIn,
    CustodyOut,
    EffectIn,
    EffectOut,
    MarkIn,
    MarkOut,
    PmCaseIn,
    PmCaseOut,
    PmCaseSummary,
    PmCaseUpdate,
)
from app.services import audit
from app.services.numbering import next_number, normalize_scene_ref

router = APIRouter(prefix="/api/pm", tags=["Post Mortem"])

CASE_FIELDS = [
    "recovery_date", "recovery_place", "state_of_body", "sex", "sex_reason", "age_min_years",
    "age_max_years", "age_method", "height_min_cm", "height_max_cm", "weight_min_kg", "weight_max_kg",
    "build", "height_certainty", "category_status", "form_data", "status",
]


def _out(db: Session, case: PmCase) -> PmCaseOut:
    out = PmCaseOut.model_validate(case)
    out.custody = [CustodyOut.model_validate(c) for c in db.scalars(
        select(CustodyEvent).where(CustodyEvent.pm_case_id == case.id).order_by(CustodyEvent.occurred_at))]
    return out


@router.get("", response_model=list[PmCaseSummary])
def list_cases(q: str | None = None, status_: str | None = Query(None, alias="status"),
               ctx: Ctx = Depends(require("pm:read")), db: Session = Depends(get_db)):
    stmt = select(PmCase).where(PmCase.operation_id == ctx.operation_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(PmCase.pm_number.ilike(like), PmCase.recovery_place.ilike(like)))
    if status_:
        stmt = stmt.where(PmCase.status == status_)
    return list(db.scalars(stmt.order_by(PmCase.pm_number)))


@router.post("", response_model=PmCaseOut, status_code=201)
def create_case(body: PmCaseIn, ctx: Ctx = Depends(require("pm:write")), db: Session = Depends(get_db)):
    op = db.get(Operation, ctx.operation_id)
    try:
        scene = normalize_scene_ref(body.scene_ref)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    data = body.model_dump(exclude={"scene_ref"})
    if data.get("status") is None:
        data["status"] = "RASCUNHO"
    case = PmCase(
        **data,
        scene_ref=scene,
        operation_id=ctx.operation_id,
        origin_base_id=ctx.base_id,
        pm_number=next_number(db, op, "PM", scene),
        created_by=ctx.user.id,
        updated_by=ctx.user.id,
    )
    db.add(case)
    db.flush()
    audit.record(db, "PM_CRIADO", ctx=ctx, object_type="pm_case", object_id=case.id,
                 details={"pm_number": case.pm_number, **audit.diff({}, data)})
    db.commit()
    db.refresh(case)
    return _out(db, case)


@router.get("/{case_id}", response_model=PmCaseOut)
def get_case(case_id: uuid.UUID, ctx: Ctx = Depends(require("pm:read")), db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    audit.record(db, "PM_CONSULTADO", ctx=ctx, object_type="pm_case", object_id=case.id)
    db.commit()
    return _out(db, case)


@router.put("/{case_id}", response_model=PmCaseOut)
def update_case(case_id: uuid.UUID, body: PmCaseUpdate, ctx: Ctx = Depends(require("pm:write")),
                db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    if case.version != body.expected_version:
        raise common.version_conflict()
    before = common.snapshot(case, CASE_FIELDS)
    data = body.model_dump(exclude={"expected_version", "scene_ref"}, exclude_unset=True)
    if data.get("status") is None:
        data.pop("status", None)
    for k, v in data.items():
        setattr(case, k, v)
    common.touch(case, ctx)
    audit.record(db, "PM_ALTERADO", ctx=ctx, object_type="pm_case", object_id=case.id,
                 details=audit.diff(before, common.snapshot(case, CASE_FIELDS)))
    db.commit()
    db.refresh(case)
    return _out(db, case)


@router.post("/{case_id}/marks", response_model=MarkOut, status_code=201)
def add_mark(case_id: uuid.UUID, body: MarkIn, ctx: Ctx = Depends(require("pm:write")),
             db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    mark = common.add_mark(db, ctx, case, body)
    db.commit()
    db.refresh(mark)
    return mark


@router.delete("/{case_id}/marks/{mark_id}", status_code=204)
def delete_mark(case_id: uuid.UUID, mark_id: uuid.UUID, ctx: Ctx = Depends(require("pm:write")),
                db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    common.remove_mark(db, ctx, case, mark_id)
    db.commit()


@router.post("/{case_id}/effects", response_model=EffectOut, status_code=201)
def add_effect(case_id: uuid.UUID, body: EffectIn, ctx: Ctx = Depends(require("pm:write")),
               db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    eff = common.add_effect(db, ctx, case, body)
    db.commit()
    db.refresh(eff)
    return eff


@router.delete("/{case_id}/effects/{effect_id}", status_code=204)
def delete_effect(case_id: uuid.UUID, effect_id: uuid.UUID, ctx: Ctx = Depends(require("pm:write")),
                  db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    common.remove_effect(db, ctx, case, effect_id)
    db.commit()


@router.post("/{case_id}/custody", response_model=CustodyOut, status_code=201)
def add_custody(case_id: uuid.UUID, body: CustodyIn, ctx: Ctx = Depends(require("pm:write")),
                db: Session = Depends(get_db)):
    """Eventos de custódia são somente-inclusão: correções se fazem com novo evento."""
    case = common.get_case(db, ctx, PmCase, case_id)
    ev = CustodyEvent(**body.model_dump(), pm_case_id=case.id, recorded_by=ctx.user.id)
    db.add(ev)
    common.touch(case, ctx)
    db.flush()
    audit.record(db, "PM_CUSTODIA_REGISTRADA", ctx=ctx, object_type="pm_case", object_id=case.id,
                 details={"evento_id": ev.id, **body.model_dump(mode="json")})
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/{case_id}/history")
def case_history(case_id: uuid.UUID, ctx: Ctx = Depends(require("pm:read")), db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, PmCase, case_id)
    att_ids = [str(a) for a in db.scalars(select(Attachment.id).where(Attachment.pm_case_id == case.id))]
    return common.history(db, [str(case.id), *att_ids])
