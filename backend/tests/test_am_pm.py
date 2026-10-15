import re

from sqlalchemy import text

from app.db import SessionLocal, reset_engine
from tests.conftest import Api


def test_cadastro_am_parcial_e_edicao(am_user):
    r = am_user.post("/api/am", json={"family_name": "TESTE PARCIAL", "sex": "F"})
    assert r.status_code == 201, r.text
    case = r.json()
    assert re.fullmatch(r"AM55-\d{4}", case["am_number"])
    assert case["status"] == "RASCUNHO" and case["version"] == 1
    upd = {"expected_version": 1, "given_names": "FULANA", "height_min_cm": 160, "height_max_cm": 165,
           "form_data": {"nominal": {"235_occupation": "Professora (fictícia)"}}}
    r = am_user.put(f"/api/am/{case['id']}", json=upd)
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2
    assert r.json()["family_name"] == "TESTE PARCIAL"  # campos não enviados são preservados
    # conflito de versão (edição concorrente)
    assert am_user.put(f"/api/am/{case['id']}", json=upd).status_code == 409
    hist = am_user.get(f"/api/am/{case['id']}/history").json()
    alter = [h for h in hist if h["action"] == "AM_ALTERADO"][0]
    assert alter["details"]["given_names"] == [None, "FULANA"]


def test_validacoes_am(am_user):
    assert am_user.post("/api/am", json={"sex": "X"}).status_code == 422
    assert am_user.post("/api/am", json={"height_min_cm": 180, "height_max_cm": 170}).status_code == 422
    case = am_user.post("/api/am", json={}).json()
    bad_region = {"mark_type": "3", "region": "99", "certainty": "RELATADO"}
    assert am_user.post(f"/api/am/{case['id']}/marks", json=bad_region).status_code == 422
    pm_certainty = {"mark_type": "3", "region": "32", "certainty": "OBSERVADO"}
    assert am_user.post(f"/api/am/{case['id']}/marks", json=pm_certainty).status_code == 422
    bad_colour = {"field_code": "300", "item_code": "302", "colour": "AZULZINHO", "certainty": "RELATADO"}
    assert am_user.post(f"/api/am/{case['id']}/effects", json=bad_colour).status_code == 422


def test_duplicidade_am_bloqueada(am_user):
    body = {"family_name": "DUPLO", "given_names": "CASO", "date_of_birth": "1980-01-01"}
    assert am_user.post("/api/am", json=body).status_code == 201
    r = am_user.post("/api/am", json=body)
    assert r.status_code == 409 and "AM55-" in r.json()["detail"]


def test_entrevistas_sinais_e_itens(am_user):
    case = am_user.post("/api/am", json={"family_name": "COM ENTREVISTAS"}).json()
    cid = case["id"]
    for name in ("MÃE FICTÍCIA", "IRMÃO FICTÍCIO"):
        r = am_user.post(f"/api/am/{cid}/interviews", json={"informant_name": name, "relationship_to_missing": "x",
                                                            "interview_date": "2026-03-12"})
        assert r.status_code == 201
    m = am_user.post(f"/api/am/{cid}/marks", json={"mark_type": "3", "region": "32", "description": "âncora",
                                                   "certainty": "RELATADO"}).json()
    am_user.post(f"/api/am/{cid}/effects", json={"field_code": "335", "item_code": "08", "colour": "GOLD",
                                                 "certainty": "DOCUMENTADO"})
    full = am_user.get(f"/api/am/{cid}").json()
    assert len(full["interviews"]) == 2 and len(full["marks"]) == 1 and len(full["effects"]) == 1
    assert am_user.delete(f"/api/am/{cid}/marks/{m['id']}").status_code == 204
    assert am_user.get(f"/api/am/{cid}").json()["marks"] == []
    hist = am_user.get(f"/api/am/{cid}/history").json()
    removed = [h for h in hist if h["action"] == "AM_SINAL_REMOVIDO"][0]
    assert removed["details"]["antes"]["description"] == "âncora"


def test_cadastro_pm_numeracao_e_custodia(pm_user):
    r = pm_user.post("/api/pm", json={"scene_ref": "hs", "state_of_body": "COMPLETO", "sex": "M",
                                      "age_min_years": 30, "age_max_years": 45})
    assert r.status_code == 201, r.text
    pm = r.json()
    assert re.fullmatch(r"PM55-\d{4}-HS", pm["pm_number"])
    assert pm_user.post("/api/pm", json={"scene_ref": "A B"}).status_code == 422
    r = pm_user.post(f"/api/pm/{pm['id']}/custody", json={"event_type": "RECEBIMENTO",
                                                          "occurred_at": "2026-03-11T10:00:00-03:00",
                                                          "responsible": "Perito Fictício"})
    assert r.status_code == 201
    r = pm_user.post(f"/api/pm/{pm['id']}/marks", json={"mark_type": "1", "region": "25", "certainty": "OBSERVADO"})
    assert r.status_code == 201
    full = pm_user.get(f"/api/pm/{pm['id']}").json()
    assert len(full["custody"]) == 1 and len(full["marks"]) == 1


def test_isolamento_am_pm(am_user, pm_user):
    am_case = am_user.post("/api/am", json={"family_name": "ISOLAMENTO"}).json()
    pm_case = pm_user.post("/api/pm", json={}).json()
    # Operador PM não lê nem altera AM
    assert pm_user.get(f"/api/am/{am_case['id']}").status_code == 403
    assert pm_user.put(f"/api/am/{am_case['id']}", json={"expected_version": 1, "sex": "M"}).status_code == 403
    assert pm_user.post(f"/api/am/{am_case['id']}/marks",
                        json={"mark_type": "1", "region": "01", "certainty": "OBSERVADO"}).status_code == 403
    # Operador AM não lê nem altera PM
    assert am_user.get(f"/api/pm/{pm_case['id']}").status_code == 403
    assert am_user.put(f"/api/pm/{pm_case['id']}", json={"expected_version": 1}).status_code == 403
    # Nenhum dos dois acessa a reconciliação
    assert am_user.get("/api/matching/overview").status_code == 403
    assert pm_user.get("/api/matching/overview").status_code == 403


def test_isolamento_por_operacao(am_user):
    """Registro de outra operação não é acessível mesmo com o UUID correto."""
    with SessionLocal() as db:
        db.execute(text("""
            WITH op AS (INSERT INTO operations (id, code, name, kind, status, country_code, created_at, updated_at)
                        VALUES (gen_random_uuid(), 'OUTRA-OP', 'Outra operação', 'TREINAMENTO', 'ATIVA', '55',
                                now(), now()) RETURNING id),
                 b AS (INSERT INTO bases (id, operation_id, code, name, kind, created_at, updated_at)
                       SELECT gen_random_uuid(), id, 'AM', 'AM', 'AM', now(), now() FROM op RETURNING id, operation_id),
                 u AS (SELECT id FROM users WHERE username = 'operador.am')
            INSERT INTO am_cases (id, operation_id, origin_base_id, am_number, status, category_status, form_data,
                                  created_by, updated_by, version, created_at, updated_at)
            SELECT 'aaaaaaaa-0000-4000-8000-000000000001', b.operation_id, b.id, 'AM55-9999', 'RASCUNHO', '{}',
                   '{}', u.id, u.id, 1, now(), now() FROM b, u
        """))
        db.commit()
    assert am_user.get("/api/am/aaaaaaaa-0000-4000-8000-000000000001").status_code == 404
    assert all(c["am_number"] != "AM55-9999" for c in am_user.get("/api/am").json())


def test_persistencia_apos_reinicio(am_user):
    case = am_user.post("/api/am", json={"family_name": "PERSISTENTE"}).json()
    # Simula reinício: descarta pool de conexões e aplicação, cria novos
    reset_engine()
    fresh = Api("operador.am").use("AM", "OPERADOR_AM")
    assert fresh.get(f"/api/am/{case['id']}").json()["family_name"] == "PERSISTENTE"


def test_auditoria_e_imutavel():
    import pytest
    from sqlalchemy.exc import DBAPIError

    with SessionLocal() as db:
        with pytest.raises(DBAPIError):
            db.execute(text("UPDATE audit_events SET action = 'X'"))
        db.rollback()
        with pytest.raises(DBAPIError):
            db.execute(text("DELETE FROM audit_events"))
        db.rollback()
