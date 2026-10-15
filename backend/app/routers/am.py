import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import Ctx, require
from app.models import AmCase, AmInterview, Attachment, Operation
from app.routers import common
from app.schemas import (
    AmCaseIn,
    AmCaseOut,
    AmCaseSummary,
    AmCaseUpdate,
    EffectIn,
    EffectOut,
    InterviewIn,
    InterviewOut,
    MarkIn,
    MarkOut,
)
from app.services import audit
from app.services.numbering import next_number

router = APIRouter(prefix="/api/am", tags=["Ante Mortem"])

CASE_FIELDS = [
    "family_name", "given_names", "sex", "date_of_birth", "age_years", "height_min_cm",
    "height_max_cm", "weight_min_kg", "weight_max_kg", "build", "height_certainty",
    "category_status", "form_data", "status",
]


@router.get("", response_model=list[AmCaseSummary])
def list_cases(q: str | None = None, status_: str | None = Query(None, alias="status"),
               ctx: Ctx = Depends(require("am:read")), db: Session = Depends(get_db)):
    stmt = select(AmCase).where(AmCase.operation_id == ctx.operation_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(AmCase.am_number.ilike(like), AmCase.family_name.ilike(like),
                              AmCase.given_names.ilike(like)))
    if status_:
        stmt = stmt.where(AmCase.status == status_)
    return list(db.scalars(stmt.order_by(AmCase.am_number)))


@router.post("", response_model=AmCaseOut, status_code=201)
def create_case(body: AmCaseIn, ctx: Ctx = Depends(require("am:write")), db: Session = Depends(get_db)):
    op = db.get(Operation, ctx.operation_id)
    data = body.model_dump(exclude_unset=False)
    if data.get("status") is None:
        data["status"] = "RASCUNHO"
    # Aviso contra duplicação inadvertida: mesmo nome + data de nascimento na operação
    if body.family_name and body.given_names and body.date_of_birth:
        dup = db.scalar(select(AmCase).where(
            AmCase.operation_id == ctx.operation_id,
            AmCase.family_name.ilike(body.family_name.strip()),
            AmCase.given_names.ilike(body.given_names.strip()),
            AmCase.date_of_birth == body.date_of_birth))
        if dup is not None:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"Já existe registro AM com mesmo nome e data de nascimento: "
                                f"{dup.am_number}. Vincule a nova entrevista ao caso existente.")
    case = AmCase(
        **data,
        operation_id=ctx.operation_id,
        origin_base_id=ctx.base_id,
        am_number=next_number(db, op, "AM"),
        created_by=ctx.user.id,
        updated_by=ctx.user.id,
    )
    db.add(case)
    db.flush()
    audit.record(db, "AM_CRIADO", ctx=ctx, object_type="am_case", object_id=case.id,
                 details={"am_number": case.am_number, **audit.diff({}, data)})
    db.commit()
    db.refresh(case)
    return case


@router.get("/{case_id}", response_model=AmCaseOut)
def get_case(case_id: uuid.UUID, ctx: Ctx = Depends(require("am:read")), db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    audit.record(db, "AM_CONSULTADO", ctx=ctx, object_type="am_case", object_id=case.id)
    db.commit()
    return case


@router.put("/{case_id}", response_model=AmCaseOut)
def update_case(case_id: uuid.UUID, body: AmCaseUpdate, ctx: Ctx = Depends(require("am:write")),
                db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    if case.version != body.expected_version:
        raise common.version_conflict()
    before = common.snapshot(case, CASE_FIELDS)
    data = body.model_dump(exclude={"expected_version"}, exclude_unset=True)
    if data.get("status") is None:
        data.pop("status", None)
    for k, v in data.items():
        setattr(case, k, v)
    if case.status == "PRONTO_RECONCILIACAO":
        common.ensure_ready(common.am_missing(case))
    common.touch(case, ctx)
    audit.record(db, "AM_ALTERADO", ctx=ctx, object_type="am_case", object_id=case.id,
                 details=audit.diff(before, common.snapshot(case, CASE_FIELDS)))
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/interviews", response_model=InterviewOut, status_code=201)
def add_interview(case_id: uuid.UUID, body: InterviewIn, ctx: Ctx = Depends(require("am:write")),
                  db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    iv = AmInterview(**body.model_dump(), am_case_id=case.id, interviewer_id=ctx.user.id)
    db.add(iv)
    common.touch(case, ctx)
    db.flush()
    audit.record(db, "AM_ENTREVISTA_INCLUIDA", ctx=ctx, object_type="am_case", object_id=case.id,
                 details={"entrevista_id": iv.id, "informante": body.informant_name,
                          "vinculo": body.relationship_to_missing})
    db.commit()
    db.refresh(iv)
    return iv


@router.put("/{case_id}/interviews/{interview_id}", response_model=InterviewOut)
def update_interview(case_id: uuid.UUID, interview_id: uuid.UUID, body: InterviewIn,
                     ctx: Ctx = Depends(require("am:write")), db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    iv = db.get(AmInterview, interview_id)
    if iv is None or iv.am_case_id != case.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entrevista não encontrada neste registro.")
    fields = list(InterviewIn.model_fields)
    before = common.snapshot(iv, fields)
    for k, v in body.model_dump().items():
        setattr(iv, k, v)
    common.touch(case, ctx)
    audit.record(db, "AM_ENTREVISTA_ALTERADA", ctx=ctx, object_type="am_case", object_id=case.id,
                 details={"entrevista_id": iv.id, **audit.diff(before, common.snapshot(iv, fields))})
    db.commit()
    db.refresh(iv)
    return iv


@router.post("/{case_id}/marks", response_model=MarkOut, status_code=201)
def add_mark(case_id: uuid.UUID, body: MarkIn, ctx: Ctx = Depends(require("am:write")),
             db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    mark = common.add_mark(db, ctx, case, body)
    db.commit()
    db.refresh(mark)
    return mark


@router.delete("/{case_id}/marks/{mark_id}", status_code=204)
def delete_mark(case_id: uuid.UUID, mark_id: uuid.UUID, ctx: Ctx = Depends(require("am:write")),
                db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    common.remove_mark(db, ctx, case, mark_id)
    db.commit()


@router.post("/{case_id}/effects", response_model=EffectOut, status_code=201)
def add_effect(case_id: uuid.UUID, body: EffectIn, ctx: Ctx = Depends(require("am:write")),
               db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    eff = common.add_effect(db, ctx, case, body)
    db.commit()
    db.refresh(eff)
    return eff


@router.delete("/{case_id}/effects/{effect_id}", status_code=204)
def delete_effect(case_id: uuid.UUID, effect_id: uuid.UUID, ctx: Ctx = Depends(require("am:write")),
                  db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    common.remove_effect(db, ctx, case, effect_id)
    db.commit()


@router.get("/{case_id}/history")
def case_history(case_id: uuid.UUID, ctx: Ctx = Depends(require("am:read")), db: Session = Depends(get_db)):
    case = common.get_case(db, ctx, AmCase, case_id)
    att_ids = [str(a) for a in db.scalars(select(Attachment.id).where(Attachment.am_case_id == case.id))]
    return common.history(db, [str(case.id), *att_ids])
