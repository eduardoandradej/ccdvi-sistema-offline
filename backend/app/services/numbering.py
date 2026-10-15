"""Numeração AM/PM conforme INTERPOL DVI Guide, Anexo 9 (ex.: AM55-0006, PM55-0025-A)."""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import NumberCounter, Operation

SCENE_RE = re.compile(r"^[A-Z0-9]{1,6}$")


def next_number(db: Session, operation: Operation, kind: str, scene_ref: str | None = None) -> str:
    assert kind in ("AM", "PM")
    counter = db.scalar(
        select(NumberCounter)
        .where(NumberCounter.operation_id == operation.id, NumberCounter.kind == kind)
        .with_for_update()
    )
    if counter is None:
        counter = NumberCounter(operation_id=operation.id, kind=kind, last_value=0)
        db.add(counter)
        db.flush()
        counter = db.scalar(
            select(NumberCounter)
            .where(NumberCounter.operation_id == operation.id, NumberCounter.kind == kind)
            .with_for_update()
        )
    counter.last_value += 1
    # Anexo 9: 4 dígitos; acima de 9.999 acrescenta-se um zero (5 dígitos).
    width = 4 if counter.last_value < 10000 else 5
    number = f"{kind}{operation.country_code}-{counter.last_value:0{width}d}"
    if kind == "PM" and scene_ref:
        number += f"-{scene_ref}"
    return number


def normalize_scene_ref(scene_ref: str | None) -> str | None:
    if scene_ref is None or scene_ref.strip() == "":
        return None
    value = scene_ref.strip().upper()
    if not SCENE_RE.match(value):
        raise ValueError("Referência de cena deve conter de 1 a 6 letras/dígitos (ex.: A, B, HS).")
    return value

