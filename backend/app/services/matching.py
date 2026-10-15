"""Motor de comparação AM × PM — explicável, determinístico e apenas de APOIO.

Princípios (Guia DVI 2023, cap. 6 e Anexo 6):
- Nenhum resultado representa identificação. A identificação é atribuição do
  Identification Board, com base preferencialmente em identificadores primários
  (papiloscopia, odontologia, DNA).
- "Não informado", "não observado", "não examinável" e "desconhecido" NUNCA viram
  incompatibilidade; só um registro explicitamente NEGATIVO pode gerar divergência.
- RapidFuzz é usado só como indicador auxiliar de semelhança textual, após normalização.
- O "índice técnico" serve apenas para ordenar candidatos; NÃO é probabilidade.
"""

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date

from rapidfuzz import fuzz

from app.vocab import (
    EFFECT_FIELDS,
    EFFECT_ITEMS,
    MARK_TYPES,
    REGIONS,
    TATTOO_MOTIF_CATEGORIES,
    contralateral,
)

ALGORITHM_VERSION = "0.1.0"

DEFAULT_PARAMS = {
    "age_margin_years": 5,
    "height_tolerance_cm": 5,
    "text_similarity_threshold": 70,
    "weights": {
        "sex": 1.0,
        "age": 1.0,
        "height": 1.0,
        "mark_same_region": 3.0,
        "mark_motif": 1.0,
        "effect": 1.0,
        "implant_serial": 5.0,
        "divergence_penalty": 3.0,
    },
}

DISCLAIMER = (
    "Instrumento de apoio à análise pericial. Os resultados indicam candidatos para revisão humana "
    "e NÃO constituem identificação. O índice técnico é experimental, serve apenas para ordenação, "
    "não foi calibrado e não representa probabilidade."
)

# Desfechos por atributo
COINCIDENTE = "COINCIDENTE"
COMPATIVEL = "COMPATIVEL"
DIVERGENTE = "DIVERGENTE"
SEM_DADOS = "SEM_DADOS"  # ausente em um ou ambos os lados: não pesa contra
INCONCLUSIVO = "INCONCLUSIVO"
INFORMATIVO = "INFORMATIVO"


@dataclass
class FieldResult:
    attribute: str
    field_code: str
    outcome: str
    am_value: str | None
    pm_value: str | None
    explanation: str
    critical: bool = False
    text_similarity: float | None = None
    score: float = 0.0


@dataclass
class ComparisonResult:
    am_case_id: str
    pm_case_id: str
    am_number: str
    pm_number: str
    technical_index: float
    coincidences: int
    divergences: int
    critical_divergences: int
    missing: int
    results: list[FieldResult] = field(default_factory=list)
    algorithm_version: str = ALGORITHM_VERSION
    parameters: dict = field(default_factory=dict)
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


# ------------------------------------------------------------------ normalização


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def text_similarity(a: str | None, b: str | None) -> float | None:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return None
    return round(float(fuzz.token_set_ratio(na, nb)), 1)


def motif_categories(text: str | None) -> set[str]:
    words = set(normalize_text(text).split())
    found = set()
    for cat, terms in TATTOO_MOTIF_CATEGORIES.items():
        norm_terms = {normalize_text(t) for t in terms}
        if words & norm_terms:
            found.add(cat)
    return found


# ------------------------------------------------------------------ entradas simples


@dataclass
class MarkIn:
    mark_type: str
    region: str
    description: str | None
    certainty: str


@dataclass
class EffectIn:
    field_code: str
    item_code: str
    type_style: str | None
    colour: str | None
    brand: str | None
    material: str | None
    inscription: str | None
    serial_number: str | None
    description: str | None


@dataclass
class AmIn:
    id: str
    number: str
    sex: str | None
    age_years: int | None
    date_of_birth: date | None
    height_min_cm: int | None
    height_max_cm: int | None
    category_status: dict
    marks: list[MarkIn]
    effects: list[EffectIn]


@dataclass
class PmIn:
    id: str
    number: str
    sex: str | None
    age_min_years: int | None
    age_max_years: int | None
    height_min_cm: int | None
    height_max_cm: int | None
    state_of_body: str | None
    category_status: dict
    marks: list[MarkIn]
    effects: list[EffectIn]


def _age_at(dob: date, ref: date) -> int:
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def _fmt_range(lo, hi, unit: str) -> str | None:
    if lo is None and hi is None:
        return None
    if lo is not None and hi is not None and lo != hi:
        return f"{lo}–{hi} {unit}"
    return f"{lo if lo is not None else hi} {unit}"


# ------------------------------------------------------------------ comparadores


def compare_sex(am: AmIn, pm: PmIn, w: dict) -> FieldResult:
    labels_am = {"M": "Masculino", "F": "Feminino", "O": "Outro", "U": "Desconhecido"}
    labels_pm = {"M": "Masculino", "F": "Feminino", "I": "Indeterminado"}
    a, p = am.sex, pm.sex
    av, pv = labels_am.get(a) if a else None, labels_pm.get(p) if p else None
    if a in (None, "U", "O") or p in (None, "I"):
        return FieldResult("Sexo", "AM cab. / PM 535", SEM_DADOS, av, pv,
                           "Sexo não informado, desconhecido ou indeterminado em um dos registros; "
                           "não pesa contra o par.")
    if a == p:
        return FieldResult("Sexo", "AM cab. / PM 535", COINCIDENTE, av, pv, "Sexo coincidente.",
                           score=w["sex"])
    return FieldResult("Sexo", "AM cab. / PM 535", DIVERGENTE, av, pv,
                       "Sexo informado no AM difere do sexo estimado no PM. Verificar a fonte e o "
                       "método de estimativa antes de descartar.", critical=True,
                       score=-w["divergence_penalty"])


def compare_age(am: AmIn, pm: PmIn, ref_date: date | None, params: dict, w: dict) -> FieldResult:
    margin = params["age_margin_years"]
    am_age = am.age_years
    basis = "idade informada"
    if am.date_of_birth and ref_date:
        am_age = _age_at(am.date_of_birth, ref_date)
        basis = "calculada pela data de nascimento e data do desastre"
    pv = _fmt_range(pm.age_min_years, pm.age_max_years, "anos")
    av = f"{am_age} anos ({basis})" if am_age is not None else None
    if am_age is None or (pm.age_min_years is None and pm.age_max_years is None):
        return FieldResult("Idade", "AM cab. / PM 540", SEM_DADOS, av, pv,
                           "Idade ausente em um dos registros; não pesa contra o par.")
    lo = pm.age_min_years if pm.age_min_years is not None else pm.age_max_years
    hi = pm.age_max_years if pm.age_max_years is not None else pm.age_min_years
    if lo <= am_age <= hi:
        return FieldResult("Idade", "AM cab. / PM 540", COMPATIVEL, av, pv,
                           "Idade AM dentro da faixa estimada no PM.", score=w["age"])
    if lo - margin <= am_age <= hi + margin:
        return FieldResult("Idade", "AM cab. / PM 540", INCONCLUSIVO, av, pv,
                           f"Idade AM fora da faixa PM, mas dentro da margem de ±{margin} anos "
                           "(estimativas etárias têm incerteza).")
    return FieldResult("Idade", "AM cab. / PM 540", DIVERGENTE, av, pv,
                       f"Idade AM fora da faixa estimada no PM mesmo com margem de ±{margin} anos.",
                       critical=True, score=-w["divergence_penalty"])


def compare_height(am: AmIn, pm: PmIn, params: dict, w: dict) -> FieldResult:
    tol = params["height_tolerance_cm"]
    av = _fmt_range(am.height_min_cm, am.height_max_cm, "cm")
    pv = _fmt_range(pm.height_min_cm, pm.height_max_cm, "cm")
    if av is None or pv is None:
        return FieldResult("Estatura", "408", SEM_DADOS, av, pv,
                           "Estatura ausente em um dos registros; não pesa contra o par.")
    a_lo = am.height_min_cm if am.height_min_cm is not None else am.height_max_cm
    a_hi = am.height_max_cm if am.height_max_cm is not None else am.height_min_cm
    p_lo = pm.height_min_cm if pm.height_min_cm is not None else pm.height_max_cm
    p_hi = pm.height_max_cm if pm.height_max_cm is not None else pm.height_min_cm
    gap = max(p_lo - a_hi, a_lo - p_hi, 0)
    caveat = " Estatura relatada por familiares e estatura estimada no PM têm incerteza."
    if gap <= tol:
        return FieldResult("Estatura", "408", COMPATIVEL, av, pv,
                           f"Faixas de estatura compatíveis (diferença {gap} cm, tolerância {tol} cm)."
                           + caveat, score=w["height"])
    if gap <= 2 * tol:
        return FieldResult("Estatura", "408", INCONCLUSIVO, av, pv,
                           f"Diferença de {gap} cm, acima da tolerância de {tol} cm." + caveat)
    return FieldResult("Estatura", "408", DIVERGENTE, av, pv,
                       f"Diferença de {gap} cm entre as faixas de estatura." + caveat,
                       score=-w["divergence_penalty"] / 2)


def _mark_label(m: MarkIn) -> str:
    desc = f" — {m.description}" if m.description else ""
    return f"{MARK_TYPES.get(m.mark_type, m.mark_type)} em {REGIONS.get(m.region, m.region)}{desc}"


def compare_marks(am: AmIn, pm: PmIn, params: dict, w: dict) -> list[FieldResult]:
    results: list[FieldResult] = []
    used_pm: set[int] = set()
    thr = params["text_similarity_threshold"]
    for am_mark in am.marks:
        tname = MARK_TYPES.get(am_mark.mark_type, am_mark.mark_type)
        attr = f"{tname} — {REGIONS.get(am_mark.region, am_mark.region)}"
        same = [(i, m) for i, m in enumerate(pm.marks)
                if m.mark_type == am_mark.mark_type and m.region == am_mark.region and i not in used_pm]
        if same:
            i, pm_mark = same[0]
            used_pm.add(i)
            sim = text_similarity(am_mark.description, pm_mark.description)
            score = w["mark_same_region"]
            expl = f"{tname} registrada na mesma região anatômica e lateralidade nos dois registros."
            if am_mark.mark_type == "3":
                cat_am, cat_pm = motif_categories(am_mark.description), motif_categories(pm_mark.description)
                common = cat_am & cat_pm
                if common:
                    score += w["mark_motif"]
                    expl += (f" Categoria de motivo compatível pelo vocabulário controlado: "
                             f"{', '.join(sorted(common))}.")
                elif cat_am and cat_pm:
                    expl += " Categorias de motivo diferentes pelo vocabulário controlado; verificar."
            if sim is not None:
                expl += (f" Semelhança textual auxiliar (RapidFuzz) entre as descrições: {sim:.0f}/100"
                         f"{' (baixa)' if sim < thr else ''} — não é evidência conclusiva.")
            if am_mark.certainty in ("RELATADO", "INCERTO") or pm_mark.certainty in ("PROVAVEL", "INCERTO"):
                expl += " Atenção ao grau de certeza informado."
            results.append(FieldResult(attr, "404", COINCIDENTE, _mark_label(am_mark),
                                       _mark_label(pm_mark), expl, text_similarity=sim, score=score))
            continue
        contra = contralateral(am_mark.region)
        other_side = [(i, m) for i, m in enumerate(pm.marks)
                      if m.mark_type == am_mark.mark_type and contra and m.region == contra
                      and i not in used_pm]
        if other_side:
            i, pm_mark = other_side[0]
            used_pm.add(i)
            sim = text_similarity(am_mark.description, pm_mark.description)
            results.append(FieldResult(
                attr, "404", DIVERGENTE, _mark_label(am_mark), _mark_label(pm_mark),
                f"{tname} na mesma região, porém em LADO OPOSTO. Divergência de lateralidade: "
                "verificar possível erro de registro (ex.: espelhamento de fotografia) antes de concluir.",
                critical=True, text_similarity=sim, score=-w["divergence_penalty"]))
            continue
        status = (pm.category_status or {}).get(am_mark.mark_type, "NAO_INFORMADO")
        if status == "NEGATIVO":
            results.append(FieldResult(
                attr, "404", DIVERGENTE, _mark_label(am_mark), "Registrado como ausente no exame PM",
                f"O AM relata {tname.lower()} e o PM registra explicitamente que não há {tname.lower()}.",
                critical=am_mark.certainty == "DOCUMENTADO", score=-w["divergence_penalty"]))
        else:
            limit = ""
            if pm.state_of_body in ("INCOMPLETO", "SEGMENTO"):
                limit = " O corpo/segmento PM está incompleto."
            results.append(FieldResult(
                attr, "404", SEM_DADOS, _mark_label(am_mark), None,
                f"Sem registro correspondente no PM (situação: {status.replace('_', ' ').lower()})."
                f"{limit} Ausência de registro não é tratada como incompatibilidade."))
    for i, pm_mark in enumerate(pm.marks):
        if i in used_pm:
            continue
        tname = MARK_TYPES.get(pm_mark.mark_type, pm_mark.mark_type)
        status = (am.category_status or {}).get(pm_mark.mark_type, "NAO_INFORMADO")
        attr = f"{tname} — {REGIONS.get(pm_mark.region, pm_mark.region)}"
        if status == "NEGATIVO":
            results.append(FieldResult(
                attr, "404", DIVERGENTE, "Família/fonte informa não possuir", _mark_label(pm_mark),
                f"O PM observou {tname.lower()} e o AM registra que a pessoa não possuía. "
                "Relatos familiares podem ser incompletos; verificar.",
                score=-w["divergence_penalty"] / 2))
        else:
            results.append(FieldResult(
                attr, "404", INFORMATIVO, None, _mark_label(pm_mark),
                "Sinal observado no PM sem correspondente relatado no AM. Pode ser desconhecido da "
                "família; buscar informação complementar."))
    return results


def _effect_label(e: EffectIn) -> str:
    item = EFFECT_ITEMS.get(e.field_code, {}).get(e.item_code, e.item_code)
    parts = [item]
    for v in (e.type_style, e.colour, e.brand, e.material, e.inscription):
        if v:
            parts.append(v)
    if e.serial_number:
        parts.append(f"nº série {e.serial_number}")
    return " · ".join(parts)


def _effect_text(e: EffectIn) -> str:
    return " ".join(v for v in (e.type_style, e.brand, e.material, e.inscription, e.description) if v)


def compare_effects(am: AmIn, pm: PmIn, params: dict, w: dict) -> list[FieldResult]:
    results: list[FieldResult] = []
    thr = params["text_similarity_threshold"]
    used: set[int] = set()
    for a in am.effects:
        cat = EFFECT_FIELDS.get(a.field_code, a.field_code)
        candidates = [(i, p) for i, p in enumerate(pm.effects)
                      if p.field_code == a.field_code and p.item_code == a.item_code and i not in used]
        attr = f"{cat}: {EFFECT_ITEMS.get(a.field_code, {}).get(a.item_code, a.item_code)}"
        if not candidates:
            continue  # ausência de pertence no PM não é informativa (pode ter sido perdido)
        # escolhe o candidato com maior semelhança textual
        a_text = _effect_text(a)
        i, p = max(candidates, key=lambda c, t=a_text: text_similarity(t, _effect_text(c[1])) or 0)
        used.add(i)
        if a.serial_number and p.serial_number:
            same_serial = normalize_text(a.serial_number) == normalize_text(p.serial_number)
            results.append(FieldResult(
                attr, a.field_code, COINCIDENTE if same_serial else DIVERGENTE, _effect_label(a),
                _effect_label(p),
                "Números de série idênticos (identificador forte, sujeito a confirmação documental)."
                if same_serial else "Números de série diferentes.",
                critical=not same_serial and a.field_code == "515",
                score=(w["implant_serial"] if same_serial else -w["divergence_penalty"])))
            continue
        sim = text_similarity(_effect_text(a), _effect_text(p))
        colour_eq = a.colour and p.colour and a.colour == p.colour
        colour_diff = a.colour and p.colour and a.colour != p.colour and "UNKNOWN" not in (a.colour, p.colour)
        notes = []
        if colour_eq:
            notes.append("cor coincidente")
        if colour_diff:
            notes.append("cores diferentes (pode haver alteração por condições do evento)")
        if sim is not None:
            notes.append(f"semelhança textual auxiliar {sim:.0f}/100")
        outcome = COMPATIVEL if (colour_eq or (sim or 0) >= thr) and not colour_diff else INCONCLUSIVO
        results.append(FieldResult(
            attr, a.field_code, outcome, _effect_label(a), _effect_label(p),
            "Mesmo tipo de item nos dois registros; " + ("; ".join(notes) or "sem detalhes para comparar")
            + ". Pertences são evidência secundária e podem ter sido trocados ou emprestados.",
            text_similarity=sim, score=w["effect"] if outcome == COMPATIVEL else 0.0))
    return results


def compare(am: AmIn, pm: PmIn, disaster_date: date | None = None, params: dict | None = None
            ) -> ComparisonResult:
    p = {**DEFAULT_PARAMS, **(params or {})}
    p["weights"] = {**DEFAULT_PARAMS["weights"], **(params or {}).get("weights", {})}
    w = p["weights"]
    results = [
        compare_sex(am, pm, w),
        compare_age(am, pm, disaster_date, p, w),
        compare_height(am, pm, p, w),
        *compare_marks(am, pm, p, w),
        *compare_effects(am, pm, p, w),
    ]
    index = round(sum(r.score for r in results), 2)
    return ComparisonResult(
        am_case_id=am.id,
        pm_case_id=pm.id,
        am_number=am.number,
        pm_number=pm.number,
        technical_index=index,
        coincidences=sum(r.outcome in (COINCIDENTE, COMPATIVEL) for r in results),
        divergences=sum(r.outcome == DIVERGENTE for r in results),
        critical_divergences=sum(r.critical for r in results),
        missing=sum(r.outcome == SEM_DADOS for r in results),
        results=results,
        parameters=p,
    )


def rank(results: list[ComparisonResult]) -> list[ComparisonResult]:
    """Ordena para revisão: primeiro pares sem divergência crítica, depois pelo índice técnico."""
    return sorted(results, key=lambda r: (r.critical_divergences > 0, -r.technical_index, r.pm_number))


def screen_compatible(am: AmIn, pm: PmIn) -> bool:
    """Triagem inicial (Anexo 6, 6.4): exclui apenas sexo explicitamente divergente."""
    if am.sex in ("M", "F") and pm.sex in ("M", "F") and am.sex != pm.sex:
        return False
    return True
