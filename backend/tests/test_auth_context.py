from fastapi.testclient import TestClient

from tests.conftest import LAB_PASSWORD, Api


def test_login_invalido_retorna_401(api):
    c = api().c
    r = c.post("/api/auth/login", json={"username": "operador.am", "password": "errada-errada"})
    assert r.status_code == 401
    r = c.post("/api/auth/login", json={"username": "nao.existe", "password": "qualquer-coisa"})
    assert r.status_code == 401


def test_sem_autenticacao_401():
    from app.main import app

    c = TestClient(app)
    assert c.get("/api/auth/me").status_code == 401
    assert c.get("/api/am").status_code == 401


def test_me_lista_apenas_autorizacoes_da_conta(api):
    a = Api("operador.am")
    roles = {(x["base"]["code"], x["role"]) for x in a.me["authorizations"]}
    assert roles == {("AM", "OPERADOR_AM")}
    assert a.me["context"] is None
    assert a.me["permissions"] == []


def test_sem_contexto_retorna_409():
    a = Api("operador.am")
    assert a.get("/api/am").status_code == 409


def test_contexto_nao_autorizado_403_e_auditado():
    am = Api("operador.am")
    pm = Api("operador.pm")
    base_pm = pm.auth_for("PM", "OPERADOR_PM")
    # operador AM tenta, via API, assumir a base PM e a função OPERADOR_PM
    r = am.put("/api/auth/context", json={"operation_id": base_pm["operation"]["id"],
                                         "base_id": base_pm["base"]["id"], "role": "OPERADOR_PM"})
    assert r.status_code == 403
    # ...ou a própria base AM com função não concedida (elevação de privilégio)
    own = am.auth_for("AM", "OPERADOR_AM")
    r = am.put("/api/auth/context", json={"operation_id": own["operation"]["id"],
                                         "base_id": own["base"]["id"], "role": "REVISOR_RECONCILIACAO"})
    assert r.status_code == 403
    aud = Api("auditor").use("COMANDO", "AUDITOR")
    events = aud.get("/api/audit", params={"action": "TROCA_CONTEXTO", "username": "operador.am"}).json()
    assert any(e["outcome"] == "NEGADO" for e in events)


def test_usuario_multibase_alterna_contexto():
    u = Api("perito.multi").use("AM", "OPERADOR_AM")
    assert u.get("/api/am").status_code == 200
    assert u.get("/api/pm").status_code == 403
    u.use("PM", "OPERADOR_PM")
    assert u.get("/api/pm").status_code == 200
    assert u.get("/api/am").status_code == 403
    me = u.get("/api/auth/me").json()
    assert me["context"]["base"]["code"] == "PM"


def test_escrita_exige_cabecalho_csrf():
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": "operador.am", "password": LAB_PASSWORD})
    assert r.status_code == 200
    me = c.get("/api/auth/me").json()
    a = me["authorizations"][0]
    body = {"operation_id": a["operation"]["id"], "base_id": a["base"]["id"], "role": a["role"]}
    assert c.put("/api/auth/context", json=body).status_code == 403
    assert c.put("/api/auth/context", json=body, headers={"x-dvi-request": "1"}).status_code == 200


def test_logout_invalida_sessao(am_user):
    assert am_user.get("/api/am").status_code == 200
    assert am_user.post("/api/auth/logout").status_code == 200
    assert am_user.get("/api/am").status_code == 401


def test_revogacao_tem_efeito_imediato():
    adm = Api("admin.tic").use("COMANDO", "ADMIN_TIC")
    bases = {b["code"]: b["id"] for b in adm.get("/api/admin/bases").json()}
    r = adm.post("/api/admin/users", json={"username": "temp.revogacao", "full_name": "Usuário Temporário",
                                           "password": LAB_PASSWORD})
    assert r.status_code == 201
    uid = r.json()["id"]
    auth_id = adm.post("/api/admin/authorizations", json={"user_id": uid, "base_id": bases["AM"],
                                                          "role": "OPERADOR_AM"}).json()["id"]
    u = Api("temp.revogacao").use("AM", "OPERADOR_AM")
    assert u.get("/api/am").status_code == 200
    assert adm.post(f"/api/admin/authorizations/{auth_id}/revoke").status_code == 200
    assert u.get("/api/am").status_code == 409  # contexto deixou de ser válido


def test_admin_tic_nao_acessa_conteudo_sensivel():
    adm = Api("admin.tic").use("COMANDO", "ADMIN_TIC")
    assert adm.get("/api/am").status_code == 403
    assert adm.get("/api/pm").status_code == 403
    assert adm.get("/api/admin/health").status_code == 200


def test_coordenador_ve_apenas_agregados():
    co = Api("coordenador").use("COMANDO", "COORDENADOR")
    d = co.get("/api/dashboard")
    assert d.status_code == 200
    assert d.json()["am_by_status"]
    assert co.get("/api/am").status_code == 403
    assert co.get("/api/matching/overview").status_code == 403


def test_bloqueio_apos_tentativas(api):
    c = api().c
    for _ in range(5):
        c.post("/api/auth/login", json={"username": "auditor", "password": "x" * 12})
    r = c.post("/api/auth/login", json={"username": "auditor", "password": LAB_PASSWORD})
    assert r.status_code == 429
