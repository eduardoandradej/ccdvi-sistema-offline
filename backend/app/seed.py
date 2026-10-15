"""Carga de dados FICTÍCIOS de laboratório.

Uso:
    python -m app.seed                    # operação, bases e usuários de laboratório
    python -m app.seed --demo-records     # + registros AM/PM fictícios do cenário de demonstração

A senha dos usuários de laboratório vem de DVI_SEED_PASSWORD; se ausente, uma senha
aleatória é gerada e exibida UMA vez no terminal. Nenhuma senha é versionada.
"""

import argparse
import os
import secrets
import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    AmCase,
    AmInterview,
    Authorization,
    Effect,
    Operation,
    OperationalBase,
    PhysicalMark,
    PmCase,
    User,
)
from app.security import hash_password, validate_password_policy
from app.services import audit
from app.services.numbering import next_number

OPERATION = {
    "code": "SIMULADO-CCDVI-2026",
    "name": "SIMULADO CCDVI 2026",
    "kind": "TREINAMENTO",
    "country_code": "55",
    "disaster_place": "Município Fictício de Serra Azul",
    "disaster_nature": "Deslizamento de terra (cenário simulado)",
    "disaster_date": date(2026, 3, 10),
}
BASES = [
    ("COMANDO", "Base Principal — Comando e Reconciliação", "COMANDO"),
    ("AM", "Base Ante Mortem", "AM"),
    ("PM", "Base Post Mortem", "PM"),
]
USERS = [
    # username, nome, cargo, [(base, função)]
    ("operador.am", "Operadora AM Fictícia", "Agente de Polícia (fictício)", [("AM", "OPERADOR_AM")]),
    ("operador.pm", "Perito PM Fictício", "Perito Criminal (fictício)", [("PM", "OPERADOR_PM")]),
    ("revisor", "Revisora de Reconciliação Fictícia", "Perita Criminal (fictício)",
     [("COMANDO", "REVISOR_RECONCILIACAO")]),
    ("coordenador", "Coordenador Fictício", "Delegado (fictício)", [("COMANDO", "COORDENADOR")]),
    ("admin.tic", "Administrador TIC Fictício", "Analista de TI (fictício)", [("COMANDO", "ADMIN_TIC")]),
    ("auditor", "Auditora Fictícia", "Corregedoria (fictício)", [("COMANDO", "AUDITOR")]),
    ("perito.multi", "Profissional Multibase Fictício", "Papiloscopista (fictício)",
     [("AM", "OPERADOR_AM"), ("PM", "OPERADOR_PM")]),
]


def ensure_reference_data(db: Session, password: str) -> Operation:
    op = db.scalar(select(Operation).where(Operation.code == OPERATION["code"]))
    if op is None:
        op = Operation(**OPERATION)
        db.add(op)
        db.flush()
    bases = {}
    for code, name, kind in BASES:
        b = db.scalar(select(OperationalBase).where(OperationalBase.operation_id == op.id,
                                                    OperationalBase.code == code))
        if b is None:
            b = OperationalBase(operation_id=op.id, code=code, name=name, kind=kind)
            db.add(b)
            db.flush()
        bases[code] = b
    for username, full_name, title, grants in USERS:
        u = db.scalar(select(User).where(User.username == username))
        if u is None:
            u = User(username=username, full_name=full_name, job_title=title, password_hash=hash_password(password))
            db.add(u)
            db.flush()
        for base_code, role in grants:
            exists = db.scalar(select(Authorization).where(
                Authorization.user_id == u.id, Authorization.operation_id == op.id,
                Authorization.base_id == bases[base_code].id, Authorization.role == role))
            if exists is None:
                db.add(Authorization(user_id=u.id, operation_id=op.id, base_id=bases[base_code].id, role=role))
    audit.record(db, "SEED_REFERENCIA", object_type="operation", object_id=op.id,
                 details={"usuarios": [u[0] for u in USERS]})
    return op


def _am(db, op, base, user, **kw) -> AmCase:
    marks = kw.pop("marks", [])
    effects = kw.pop("effects", [])
    interviews = kw.pop("interviews", [])
    c = AmCase(operation_id=op.id, origin_base_id=base.id, am_number=next_number(db, op, "AM"),
               created_by=user.id, updated_by=user.id, status="PRONTO_RECONCILIACAO", **kw)
    db.add(c)
    db.flush()
    for t, r, d in marks:
        db.add(PhysicalMark(am_case_id=c.id, mark_type=t, region=r, description=d, certainty="RELATADO",
                            source="Entrevista com familiar (fictícia)"))
    for e in effects:
        db.add(Effect(am_case_id=c.id, certainty="RELATADO", **e))
    for iv in interviews:
        db.add(AmInterview(am_case_id=c.id, interviewer_id=user.id, **iv))
    return c


def _pm(db, op, base, user, scene="A", **kw) -> PmCase:
    marks = kw.pop("marks", [])
    effects = kw.pop("effects", [])
    c = PmCase(operation_id=op.id, origin_base_id=base.id, pm_number=next_number(db, op, "PM", scene),
               scene_ref=scene, created_by=user.id, updated_by=user.id, status="PRONTO_RECONCILIACAO", **kw)
    db.add(c)
    db.flush()
    for t, r, d in marks:
        db.add(PhysicalMark(pm_case_id=c.id, mark_type=t, region=r, description=d, certainty="OBSERVADO"))
    for e in effects:
        db.add(Effect(pm_case_id=c.id, certainty="OBSERVADO", **e))
    return c


def demo_records(db: Session, op: Operation) -> None:
    if db.scalar(select(AmCase).where(AmCase.operation_id == op.id)) is not None:
        print("Registros de demonstração já existem; nada a fazer.")
        return
    base_am = db.scalar(select(OperationalBase).where(OperationalBase.operation_id == op.id,
                                                      OperationalBase.code == "AM"))
    base_pm = db.scalar(select(OperationalBase).where(OperationalBase.operation_id == op.id,
                                                      OperationalBase.code == "PM"))
    u_am = db.scalar(select(User).where(User.username == "operador.am"))
    u_pm = db.scalar(select(User).where(User.username == "operador.pm"))
    jeans = {"field_code": "300", "item_code": "302", "type_style": "calça jeans", "colour": "BLUE",
             "brand": "Marca Fictícia"}
    # Cenário 5: AM com tatuagem de rosa (antebraço direito), cicatriz joelho esquerdo, ~1,75 m
    _am(db, op, base_am, u_am, family_name="SILVA FICTÍCIA", given_names="MARIA", sex="F",
        date_of_birth=date(1991, 5, 20), height_min_cm=175, height_max_cm=175, height_certainty="RELATADO",
        marks=[("3", "32", "tatuagem de uma rosa vermelha"), ("1", "25", "cicatriz cirúrgica no joelho")],
        effects=[jeans, {"field_code": "335", "item_code": "08", "type_style": "aliança lisa", "colour": "GOLD",
                         "inscription": "M & J 2015"}],
        interviews=[{"informant_name": "IRMÃ FICTÍCIA DA SILVA", "relationship_to_missing": "Irmã",
                     "interview_date": date(2026, 3, 12), "location": "Base AM", "is_point_of_contact": True,
                     "notes": "Entrevista fictícia para demonstração."}],
        category_status={"2": "NEGATIVO"})
    # Caso AM masculino; família afirma que NÃO tinha tatuagens
    _am(db, op, base_am, u_am, family_name="PEREIRA EXEMPLO", given_names="JOÃO", sex="M", age_years=52,
        height_min_cm=166, height_max_cm=170, marks=[("1", "11", "cicatriz de cirurgia abdominal")],
        category_status={"3": "NEGATIVO"})
    # Cenário 7: AM com quase tudo ausente
    _am(db, op, base_am, u_am, family_name="SOUZA TESTE", given_names="ANA", sex="F", age_years=29)

    # PM compatível com o cenário 5 (tatuagem floral no mesmo local, cicatriz, 1,74 m)
    _pm(db, op, base_pm, u_pm, state_of_body="COMPLETO", sex="F", age_min_years=30, age_max_years=40,
        height_min_cm=174, height_max_cm=174, recovery_date=date(2026, 3, 11), recovery_place="Setor 2 (fictício)",
        marks=[("3", "32", "tatuagem floral, possivelmente rosa"), ("1", "25", "cicatriz linear no joelho")],
        effects=[{**jeans, "brand": None}])
    # Cenário 6: tatuagem do lado oposto + outras incompatibilidades
    _pm(db, op, base_pm, u_pm, state_of_body="COMPLETO", sex="F", age_min_years=55, age_max_years=70,
        height_min_cm=158, height_max_cm=162, recovery_date=date(2026, 3, 11),
        marks=[("3", "22", "tatuagem de flor")], category_status={"1": "NEGATIVO"})
    # PM masculino incompleto
    _pm(db, op, base_pm, u_pm, scene="B", state_of_body="INCOMPLETO", sex="M", age_min_years=45,
        age_max_years=60, marks=[("1", "11", "cicatriz abdominal")])
    # Cenário 7: PM com dados ausentes
    _pm(db, op, base_pm, u_pm, scene="B", state_of_body="SEGMENTO", sex="I")
    audit.record(db, "SEED_DEMONSTRACAO", object_type="operation", object_id=op.id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo-records", action="store_true", help="cria registros AM/PM fictícios")
    args = parser.parse_args(argv)
    password = os.environ.get("DVI_SEED_PASSWORD")
    generated = password is None
    if generated:
        password = secrets.token_urlsafe(12)
    try:
        validate_password_policy(password)
    except ValueError as exc:
        print(f"DVI_SEED_PASSWORD inválida: {exc}", file=sys.stderr)
        return 2
    with SessionLocal() as db:
        op = ensure_reference_data(db, password)
        if args.demo_records:
            demo_records(db, op)
        db.commit()
    print(f"Operação: {OPERATION['name']}")
    print("Usuários de laboratório: " + ", ".join(u[0] for u in USERS))
    if generated:
        print(f"Senha gerada para usuários NOVOS (anote; não será exibida novamente): {password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
