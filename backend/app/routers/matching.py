"""Reconciliação AM × PM: candidatos para revisão humana. Não há identificação automática."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import Ctx, require
from app.models import AmCase, MatchReview, Operation, PmCase
from app.routers import common
from app.schemas import AmCaseOut, PmCaseOut, ReviewIn
from app.services import audit
from app.services import matching as m

router = APIRouter(prefix="/api/matching", tags=["reconciliação"])


def to_am_in(c: AmCase) -> m.AmIn:
    return m.AmIn(
        id=str(c.id), number=c.am_number, sex=c.sex, age_years=c.age_years, date_of_birth=c.date_of_birth,
        height_min_cm=c.height_min_cm, height_max_cm=c.height_max_cm,
        category_status=c.category_status or {},
        marks=[m.MarkIn(k.mark_type, k.region, k.description, k.certainty) for k in c.marks],
        effects=[m.EffectIn(e.field_code, e.item_code, e.type_style, e.colour, e.brand, e.material,
                            e.inscription, e.serial_number, e.description) for e in c.effects],
    )


def to_pm_in(c: PmCase) -> m.PmIn:
    return m.PmIn(
        id=str(c.id), number=c.pm_number, sex=c.sex, age_min_years=c.age_min_years,
        age_max_years=c.age_max_years, height_min_cm=c.height_min_cm, height_max_cm=c.height_max_cm,
        state_of_body=c.state_of_body, category_status=c.category_status or {},
        marks=[m.MarkIn(k.mark_type, k.region, k.description, k.certainty) for k in c.marks],
        effects=[m.EffectIn(e.field_code, e.item_code, e.type_style, e.colour, e.brand, e.material,
                            e.inscription, e.serial_number, e.description) for e in c.effects],
    )


def _reviews(db: Session, operation_id) -> dict[tuple[str, str], MatchReview]:
    rows = db.scalars(select(MatchReview).where(MatchReview.operation_id == operation_id))
    return {(str(r.am_case_id), str(r.pm_case_id)): r for r in rows}


def _summary(res: m.ComparisonResult, review: MatchReview | None) -> dict:
    return {
        "am_case_id": res.am_case_id, "pm_case_id": res.pm_case_id,
        "am_number": res.am_number, "pm_number": res.pm_number,
        "technical_index": res.technical_index, "coincidences": res.coincidences,
        "divergences": res.divergences, "critical_divergences": res.critical_divergences,
        "missing": res.missing,
        "review_status": review.status if review else None,
    }


@router.get("/candidates")
def candidates(am_case_id: uuid.UUID | None = None, pm_case_id: uuid.UUID | None = None,
               include_screened_out: bool = False, ctx: Ctx = Depends(require("match:read")),
               db: Session = Depends(get_db)):
    """Lista ordenada de candidatos para revisão a partir de um registro AM ou PM."""
    if (am_case_id is None) == (pm_case_id is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe am_case_id ou pm_case_id.")
    op = db.get(Operation, ctx.operation_id)
    reviews = _reviews(db, ctx.operation_id)
    results, screened_out = [], 0
    if am_case_id:
        am = to_am_in(common.get_case(db, ctx, AmCase, am_case_id))
        others = [to_pm_in(p) for p in db.scalars(select(PmCase).where(PmCase.operation_id == ctx.operation_id))]
        pairs = [(am, p) for p in others]
    else:
        pm = to_pm_in(common.get_case(db, ctx, PmCase, pm_case_id))
        others = [to_am_in(a) for a in db.scalars(select(AmCase).where(AmCase.operation_id == ctx.operation_id))]
        pairs = [(a, pm) for a in others]
    for a, p in pairs:
        if not include_screened_out and not m.screen_compatible(a, p):
            screened_out += 1
            continue
        results.append(m.compare(a, p, op.disaster_date))
    ranked = m.rank(results)
    audit.record(db, "RECONCILIACAO_CANDIDATOS", ctx=ctx, object_type="am_case" if am_case_id else "pm_case",
                 object_id=am_case_id or pm_case_id,
                 details={"candidatos": len(ranked), "excluidos_triagem": screened_out,
                          "algoritmo": m.ALGORITHM_VERSION})
    db.commit()
    return {
        "algorithm_version": m.ALGORITHM_VERSION,
        "disclaimer": m.DISCLAIMER,
        "screened_out": screened_out,
        "screening_rule": "Excluídos apenas pares com sexo explicitamente divergente (Anexo 6, 6.4).",
        "candidates": [_summary(r, reviews.get((r.am_case_id, r.pm_case_id))) for r in ranked],
    }


@router.get("/overview")
def overview(ctx: Ctx = Depends(require("match:read")), db: Session = Depends(get_db)):
    """Para cada AM, o melhor candidato PM (sem divergência crítica, se houver)."""
    op = db.get(Operation, ctx.operation_id)
    ams = list(db.scalars(select(AmCase).where(AmCase.operation_id == ctx.operation_id).order_by(AmCase.am_number)))
    pms = [to_pm_in(p) for p in db.scalars(select(PmCase).where(PmCase.operation_id == ctx.operation_id))]
    reviews = _reviews(db, ctx.operation_id)
    rows = []
    for a in ams:
        ai = to_am_in(a)
        res = m.rank([m.compare(ai, p, op.disaster_date) for p in pms if m.screen_compatible(ai, p)])
        top = res[0] if res else None
        rows.append({
            "am_case_id": str(a.id), "am_number": a.am_number,
            "name": " ".join(x for x in (a.given_names, a.family_name) if x) or None,
            "status": a.status, "candidates": len(res),
            "top": _summary(top, reviews.get((top.am_case_id, top.pm_case_id))) if top else None,
        })
    return {"algorithm_version": m.ALGORITHM_VERSION, "disclaimer": m.DISCLAIMER,
            "am_total": len(ams), "pm_total": len(pms), "rows": rows}


@router.get("/compare")
def compare(am_case_id: uuid.UUID, pm_case_id: uuid.UUID, ctx: Ctx = Depends(require("match:read")),
            db: Session = Depends(get_db)):
    op = db.get(Operation, ctx.operation_id)
    am = common.get_case(db, ctx, AmCase, am_case_id)
    pm = common.get_case(db, ctx, PmCase, pm_case_id)
    res = m.compare(to_am_in(am), to_pm_in(pm), op.disaster_date)
    review = _reviews(db, ctx.operation_id).get((str(am.id), str(pm.id)))
    audit.record(db, "RECONCILIACAO_COMPARACAO", ctx=ctx, object_type="match",
                 object_id=f"{am.id}:{pm.id}"[:64], details={"am": am.am_number, "pm": pm.pm_number})
    db.commit()
    return {
        "result": res.to_dict(),
        "am": AmCaseOut.model_validate(am).model_dump(mode="json"),
        "pm": PmCaseOut.model_validate(pm).model_dump(mode="json"),
        "review": None if review is None else {
            "status": review.status, "notes": review.notes, "updated_at": review.updated_at,
            "technical_index": review.technical_index, "algorithm_version": review.algorithm_version,
        },
    }


class ReviewBody(ReviewIn):
    am_case_id: uuid.UUID
    pm_case_id: uuid.UUID


@router.put("/review")
def save_review(body: ReviewBody, ctx: Ctx = Depends(require("match:review")), db: Session = Depends(get_db)):
    """Registra a análise humana do par. Os status possíveis não incluem identificação positiva."""
    op = db.get(Operation, ctx.operation_id)
    am = common.get_case(db, ctx, AmCase, body.am_case_id)
    pm = common.get_case(db, ctx, PmCase, body.pm_case_id)
    res = m.compare(to_am_in(am), to_pm_in(pm), op.disaster_date)
    review = db.scalar(select(MatchReview).where(MatchReview.am_case_id == am.id,
                                                 MatchReview.pm_case_id == pm.id))
    before = None
    if review is None:
        review = MatchReview(operation_id=ctx.operation_id, am_case_id=am.id, pm_case_id=pm.id)
        db.add(review)
    else:
        before = {"status": review.status, "notes": review.notes}
    review.status = body.status
    review.notes = body.notes
    review.algorithm_version = m.ALGORITHM_VERSION
    review.parameters = res.parameters
    review.result_snapshot = res.to_dict()
    review.technical_index = res.technical_index
    review.reviewed_by = ctx.user.id
    db.flush()
    audit.record(db, "RECONCILIACAO_REVISAO", ctx=ctx, object_type="match_review", object_id=review.id,
                 details={"am": am.am_number, "pm": pm.pm_number, "antes": before,
                          "depois": {"status": body.status, "notes": body.notes},
                          "algoritmo": m.ALGORITHM_VERSION})
    db.commit()
    return {"ok": True, "status": review.status}


class ReviewOut(BaseModel):
    am_case_id: uuid.UUID
    pm_case_id: uuid.UUID
    am_number: str
    pm_number: str
    status: str
    notes: str | None
    technical_index: float | None
    algorithm_version: str


@router.get("/reviews", response_model=list[ReviewOut])
def list_reviews(ctx: Ctx = Depends(require("match:read")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(MatchReview, AmCase.am_number, PmCase.pm_number)
        .join(AmCase, AmCase.id == MatchReview.am_case_id)
        .join(PmCase, PmCase.id == MatchReview.pm_case_id)
        .where(MatchReview.operation_id == ctx.operation_id)
        .order_by(MatchReview.updated_at.desc())
    )
    return [ReviewOut(am_case_id=r.am_case_id, pm_case_id=r.pm_case_id, am_number=an, pm_number=pn,
                      status=r.status, notes=r.notes, technical_index=r.technical_index,
                      algorithm_version=r.algorithm_version) for r, an, pn in rows]
