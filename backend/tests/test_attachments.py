import hashlib
import io

from PIL import Image

from app import demo_files
from tests.conftest import Api


def _upload(api, kind, case_id, data, filename, doc_type, subject, title="Anexo de teste"):
    return api.post("/api/attachments", data={"record_kind": kind, "case_id": case_id, "doc_type": doc_type,
                                              "subject": subject, "title": title, "source": "Teste"},
                    files={"file": (filename, data)})


def test_upload_am_foto_e_pdf_com_hash_e_download(am_user):
    case = am_user.post("/api/am", json={"family_name": "COM ANEXOS"}).json()
    photo = demo_files.reference_photo()
    r = _upload(am_user, "AM", case["id"], photo, "foto.jpg", "FOTO_REFERENCIA_AM", "DESAPARECIDO")
    assert r.status_code == 201, r.text
    att = r.json()
    assert att["sha256"] == hashlib.sha256(photo).hexdigest()
    assert att["mime_type"] == "image/jpeg" and att["status"] == "ARMAZENADO"
    for key in ("id", "doc_type", "source", "uploaded_by", "uploaded_at", "sha256"):
        assert att[key]
    pdf = demo_files.id_document_pdf()
    r = _upload(am_user, "AM", case["id"], pdf, "identidade.pdf", "DOC_IDENTIFICACAO", "DESAPARECIDO")
    assert r.status_code == 201, r.text
    assert r.json()["page_count"] == 2
    pdf_id = r.json()["id"]
    lst = am_user.get("/api/attachments", params={"am_case_id": case["id"]}).json()
    assert {a["doc_type"] for a in lst} == {"FOTO_REFERENCIA_AM", "DOC_IDENTIFICACAO"}
    dl = am_user.get(f"/api/attachments/{pdf_id}/content", params={"download": True})
    assert dl.status_code == 200 and dl.content == pdf
    assert dl.headers["cache-control"] == "no-store"
    assert am_user.get(f"/api/attachments/{att['id']}/thumbnail").status_code == 200
    assert am_user.get(f"/api/attachments/{pdf_id}/verify").json()["ok"] is True


def test_exif_gps_removido_na_visualizacao(am_user):
    case = am_user.post("/api/am", json={}).json()
    data = demo_files.jpeg_with_gps_exif()
    assert Image.open(io.BytesIO(data)).getexif().get(0x8825) is not None
    att = _upload(am_user, "AM", case["id"], data, "gps.jpg", "FOTO_REFERENCIA_AM", "DESAPARECIDO").json()
    out = am_user.get(f"/api/attachments/{att['id']}/content").content
    exif = Image.open(io.BytesIO(out)).getexif()
    assert exif.get(0x8825) is None and exif.get(0x010F) is None
    # o original continua preservado byte a byte (hash registrado = hash do arquivo enviado)
    verified = am_user.get(f"/api/attachments/{att['id']}/verify").json()
    assert verified["sha256_atual"] == hashlib.sha256(data).hexdigest()


def test_extensao_forjada_e_tipos_proibidos_rejeitados(am_user):
    case = am_user.post("/api/am", json={}).json()
    png = demo_files.object_photo()
    r = _upload(am_user, "AM", case["id"], png, "documento.pdf", "OUTRO", "DESAPARECIDO")
    assert r.status_code == 422 and "não corresponde" in r.json()["detail"]
    r = _upload(am_user, "AM", case["id"], b"#!/bin/sh\necho oi\n", "foto.jpg", "OUTRO", "DESAPARECIDO")
    assert r.status_code == 422
    r = _upload(am_user, "AM", case["id"], b"\xff\xd8\xff" + b"lixo" * 100, "foto.jpg", "OUTRO", "DESAPARECIDO")
    assert r.status_code == 422  # assinatura JPEG mas conteúdo inválido
    r = _upload(am_user, "AM", case["id"], png, "foto.png", "FOTO_ACHADO_PM", "DESAPARECIDO")
    assert r.status_code == 422  # tipo PM não se aplica a AM
    r = _upload(am_user, "AM", case["id"], png, "foto.png", "OUTRO", "REGISTRO_PM")
    assert r.status_code == 422


def test_limite_de_tamanho(am_user):
    case = am_user.post("/api/am", json={}).json()
    big = b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024 + 10)
    r = _upload(am_user, "AM", case["id"], big, "grande.pdf", "OUTRO", "DESAPARECIDO")
    assert r.status_code == 413


def test_controle_de_acesso_aos_anexos(am_user, pm_user, reviewer):
    case = am_user.post("/api/am", json={}).json()
    att = _upload(am_user, "AM", case["id"], demo_files.id_document_pdf(), "id.pdf", "DOC_IDENTIFICACAO",
                  "ENTREVISTADO").json()
    url = f"/api/attachments/{att['id']}/content"
    # operador PM não acessa anexo AM por URL direta, nem consegue anexar em AM
    assert pm_user.get(url).status_code == 403
    assert pm_user.get(f"/api/attachments/{att['id']}").status_code == 403
    r = _upload(pm_user, "AM", case["id"], demo_files.object_photo(), "x.png", "OUTRO", "DESAPARECIDO")
    assert r.status_code == 403
    # coordenador e TIC não acessam conteúdo sensível
    assert Api("coordenador").use("COMANDO", "COORDENADOR").get(url).status_code == 403
    assert Api("admin.tic").use("COMANDO", "ADMIN_TIC").get(url).status_code == 403
    # sem sessão
    from fastapi.testclient import TestClient

    from app.main import app

    assert TestClient(app).get(url).status_code == 401
    # revisor de reconciliação pode visualizar, mas não alterar
    assert reviewer.get(url).status_code == 200
    assert reviewer.post(f"/api/attachments/{att['id']}/withdraw", json={"reason": "teste de permissão"}
                         ).status_code == 403


def test_nova_versao_preserva_original_e_retirada_nao_apaga(pm_user):
    case = pm_user.post("/api/pm", json={}).json()
    v1 = _upload(pm_user, "PM", case["id"], demo_files.object_photo("v1"), "obj.png", "REGISTRO_PERTENCE",
                 "REGISTRO_PM").json()
    v2_data = demo_files.object_photo("v2")
    r = pm_user.post(f"/api/attachments/{v1['id']}/versions", files={"file": ("obj2.png", v2_data)})
    assert r.status_code == 201
    v2 = r.json()
    assert v2["version"] == 2 and v2["supersedes_id"] == v1["id"]
    current = pm_user.get("/api/attachments", params={"pm_case_id": case["id"]}).json()
    assert [a["id"] for a in current] == [v2["id"]]
    every = pm_user.get("/api/attachments", params={"pm_case_id": case["id"], "include_superseded": True}).json()
    assert {a["id"] for a in every} == {v1["id"], v2["id"]}
    assert pm_user.get(f"/api/attachments/{v1['id']}/verify").json()["ok"] is True
    r = pm_user.post(f"/api/attachments/{v2['id']}/withdraw", json={"reason": "Registrado no caso errado"})
    assert r.json()["status"] == "RETIRADO"
    assert pm_user.get(f"/api/attachments/{v2['id']}/verify").json()["ok"] is True  # arquivo mantido
    hist = pm_user.get(f"/api/pm/{case['id']}/history").json()
    actions = {h["action"] for h in hist}
    assert {"ANEXO_ENVIADO", "ANEXO_NOVA_VERSAO", "ANEXO_RETIRADO"} <= actions


def test_anexo_persiste_apos_reinicio(am_user):
    from app.db import reset_engine

    case = am_user.post("/api/am", json={}).json()
    data = demo_files.dental_record_pdf()
    att = _upload(am_user, "AM", case["id"], data, "odonto.pdf", "DOC_ODONTOLOGICO", "DESAPARECIDO").json()
    reset_engine()
    fresh = Api("operador.am").use("AM", "OPERADOR_AM")
    assert fresh.get(f"/api/attachments/{att['id']}/content").content == data
