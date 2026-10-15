from datetime import date

from app.services import matching as m


def _am(**kw):
    base = dict(id="am", number="AM55-0001", sex="F", age_years=34, date_of_birth=None, height_min_cm=175,
                height_max_cm=175, category_status={}, marks=[], effects=[])
    return m.AmIn(**{**base, **kw})


def _pm(**kw):
    base = dict(id="pm", number="PM55-0001-A", sex="F", age_min_years=30, age_max_years=40, height_min_cm=174,
                height_max_cm=174, state_of_body="COMPLETO", category_status={}, marks=[], effects=[])
    return m.PmIn(**{**base, **kw})


def by_attr(res, prefix):
    return [r for r in res.results if r.attribute.startswith(prefix)]


def test_cenario_compativel_explica_cada_semelhanca():
    am = _am(marks=[m.MarkIn("3", "32", "tatuagem de uma rosa vermelha", "RELATADO"),
                    m.MarkIn("1", "25", "cicatriz no joelho", "RELATADO")])
    pm = _pm(marks=[m.MarkIn("3", "32", "tatuagem floral", "OBSERVADO"),
                    m.MarkIn("1", "25", "cicatriz linear", "OBSERVADO")])
    res = m.compare(am, pm)
    assert res.critical_divergences == 0 and res.divergences == 0
    tattoo = by_attr(res, "Tatuagem")[0]
    assert tattoo.outcome == m.COINCIDENTE
    assert "FLORAL" in tattoo.explanation and "RapidFuzz" in tattoo.explanation
    assert by_attr(res, "Estatura")[0].outcome == m.COMPATIVEL
    assert "não" in res.disclaimer.lower() and "probabilidade" in res.disclaimer


def test_lateralidade_oposta_e_divergencias_criticas():
    am = _am(marks=[m.MarkIn("3", "32", "rosa", "RELATADO"), m.MarkIn("1", "25", "cicatriz", "DOCUMENTADO")])
    pm = _pm(age_min_years=55, age_max_years=70, height_min_cm=158, height_max_cm=162,
             marks=[m.MarkIn("3", "22", "flor", "OBSERVADO")], category_status={"1": "NEGATIVO"})
    res = m.compare(am, pm)
    tattoo = by_attr(res, "Tatuagem")[0]
    assert tattoo.outcome == m.DIVERGENTE and tattoo.critical and "LADO OPOSTO" in tattoo.explanation
    assert by_attr(res, "Idade")[0].outcome == m.DIVERGENTE
    assert by_attr(res, "Cicatriz")[0].outcome == m.DIVERGENTE
    assert res.critical_divergences >= 2


def test_ausencia_nao_e_incompatibilidade():
    am = _am(height_min_cm=None, height_max_cm=None, marks=[m.MarkIn("3", "32", "rosa", "RELATADO")])
    pm = _pm(sex="I", age_min_years=None, age_max_years=None, height_min_cm=None, height_max_cm=None,
             state_of_body="SEGMENTO")
    res = m.compare(am, pm)
    assert res.divergences == 0
    assert all(r.outcome in (m.SEM_DADOS, m.INFORMATIVO) for r in res.results)
    assert "não é tratada como incompatibilidade" in by_attr(res, "Tatuagem")[0].explanation
    # status explícito "não examinável" também não gera divergência
    pm2 = _pm(category_status={"3": "NAO_EXAMINAVEL"})
    assert by_attr(m.compare(am, pm2), "Tatuagem")[0].outcome == m.SEM_DADOS


def test_negativo_explicito_gera_divergencia():
    am = _am(marks=[m.MarkIn("3", "32", "rosa", "RELATADO")])
    pm = _pm(category_status={"3": "NEGATIVO"})
    assert by_attr(m.compare(am, pm), "Tatuagem")[0].outcome == m.DIVERGENTE


def test_idade_calculada_pela_data_de_nascimento_e_margem():
    am = _am(age_years=None, date_of_birth=date(1991, 5, 20))
    res = m.compare(am, _pm(), disaster_date=date(2026, 3, 10))
    age = by_attr(res, "Idade")[0]
    assert age.outcome == m.COMPATIVEL and "34 anos" in age.am_value
    res = m.compare(_am(age_years=43), _pm())
    assert by_attr(res, "Idade")[0].outcome == m.INCONCLUSIVO


def test_implante_numero_de_serie():
    e_am = m.EffectIn("515", "02", None, None, None, None, None, "MP-123-FICT", None)
    same = m.EffectIn("515", "02", None, None, None, None, None, "mp 123 fict", None)
    other = m.EffectIn("515", "02", None, None, None, None, None, "XX-999", None)
    assert m.compare(_am(effects=[e_am]), _pm(effects=[same])).results[-1].outcome == m.COINCIDENTE
    r = m.compare(_am(effects=[e_am]), _pm(effects=[other])).results[-1]
    assert r.outcome == m.DIVERGENTE and r.critical


def test_ordenacao_prioriza_pares_sem_divergencia_critica():
    am = _am(marks=[m.MarkIn("3", "32", "rosa", "RELATADO")])
    good = m.compare(am, _pm(id="g", number="PM55-0002", marks=[m.MarkIn("3", "32", "flor", "OBSERVADO")]))
    bad = m.compare(am, _pm(id="b", number="PM55-0001", marks=[m.MarkIn("3", "22", "flor", "OBSERVADO")],
                            category_status={}))
    assert [r.pm_case_id for r in m.rank([bad, good])] == ["g", "b"]


# ------------------------------------------------------------- API (dados do seed de demonstração)


def _find(cases, key, value):
    return next(c for c in cases if c[key] == value)


def test_api_candidatos_e_revisao(reviewer):
    ams = reviewer.get("/api/am").json()
    maria = _find(ams, "given_names", "MARIA")
    r = reviewer.get("/api/matching/candidates", params={"am_case_id": maria["id"]})
    assert r.status_code == 200
    body = r.json()
    assert body["algorithm_version"] == m.ALGORITHM_VERSION and "NÃO constituem identificação" in body["disclaimer"]
    cands = body["candidates"]
    assert body["screened_out"] >= 1  # PM masculino excluído na triagem por sexo
    top = cands[0]
    assert top["critical_divergences"] == 0 and top["coincidences"] >= 3
    assert any(c["critical_divergences"] > 0 for c in cands)
    cmp = reviewer.get("/api/matching/compare", params={"am_case_id": maria["id"],
                                                        "pm_case_id": top["pm_case_id"]}).json()
    assert cmp["am"]["am_number"] == maria["am_number"] and cmp["result"]["results"]
    # revisão humana: somente status de encaminhamento; identificação positiva não existe
    bad = reviewer.put("/api/matching/review", json={"am_case_id": maria["id"], "pm_case_id": top["pm_case_id"],
                                                     "status": "IDENTIFICADO"})
    assert bad.status_code == 422
    ok = reviewer.put("/api/matching/review", json={"am_case_id": maria["id"], "pm_case_id": top["pm_case_id"],
                                                    "status": "ENCAMINHADO_AVALIACAO_TECNICA",
                                                    "notes": "Solicitar confronto odontológico."})
    assert ok.status_code == 200
    reviews = reviewer.get("/api/matching/reviews").json()
    assert any(rv["status"] == "ENCAMINHADO_AVALIACAO_TECNICA" for rv in reviews)
    overview = reviewer.get("/api/matching/overview").json()
    assert overview["am_total"] >= 3


def test_operadores_nao_registram_revisao(am_user):
    r = am_user.put("/api/matching/review", json={"am_case_id": "00000000-0000-4000-8000-000000000000",
                                                  "pm_case_id": "00000000-0000-4000-8000-000000000000",
                                                  "status": "EM_ANALISE"})
    assert r.status_code == 403
