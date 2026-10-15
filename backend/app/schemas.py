import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app import vocab


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth / contexto


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class ContextIn(BaseModel):
    operation_id: uuid.UUID
    base_id: uuid.UUID
    role: str


class OperationOut(ORM):
    id: uuid.UUID
    code: str
    name: str
    kind: str
    status: str
    country_code: str
    disaster_place: str | None
    disaster_nature: str | None
    disaster_date: date | None


class BaseOut(ORM):
    id: uuid.UUID
    code: str
    name: str
    kind: str


class AuthorizationOut(BaseModel):
    operation: OperationOut
    base: BaseOut
    role: str
    role_label: str


class MeOut(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    job_title: str | None
    authorizations: list[AuthorizationOut]
    context: dict | None
    permissions: list[str]


# ---------------------------------------------------------------- itens comparáveis


class MarkIn(BaseModel):
    mark_type: str
    region: str
    description: str | None = Field(default=None, max_length=2000)
    certainty: str
    source: str | None = Field(default=None, max_length=200)

    @field_validator("mark_type")
    @classmethod
    def _t(cls, v: str) -> str:
        if v not in vocab.MARK_TYPES:
            raise ValueError("Tipo de sinal inválido (campo 404).")
        return v

    @field_validator("region")
    @classmethod
    def _r(cls, v: str) -> str:
        if v not in vocab.REGIONS:
            raise ValueError("Região anatômica inválida (campo 404).")
        return v

    @field_validator("certainty")
    @classmethod
    def _c(cls, v: str) -> str:
        if v not in vocab.CERTAINTIES:
            raise ValueError("Grau de certeza inválido.")
        return v


class MarkOut(MarkIn, ORM):
    id: uuid.UUID
    created_at: datetime


class EffectIn(BaseModel):
    field_code: str
    item_code: str
    type_style: str | None = Field(default=None, max_length=200)
    colour: str | None = None
    brand: str | None = Field(default=None, max_length=120)
    material: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=40)
    inscription: str | None = Field(default=None, max_length=200)
    where_worn: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    certainty: str

    @model_validator(mode="after")
    def _check(self):
        if self.field_code not in vocab.EFFECT_FIELDS:
            raise ValueError("Categoria de item inválida (campos 300–350/515).")
        if self.item_code not in vocab.EFFECT_ITEMS.get(self.field_code, {}):
            raise ValueError("Código de item inválido para a categoria.")
        if self.colour is not None and self.colour not in vocab.COLOURS:
            raise ValueError("Cor fora da lista do formulário INTERPOL.")
        if self.certainty not in vocab.CERTAINTIES:
            raise ValueError("Grau de certeza inválido.")
        return self


class EffectOut(EffectIn, ORM):
    id: uuid.UUID
    created_at: datetime


def _check_category_status(v: dict[str, str]) -> dict[str, str]:
    for k, s in v.items():
        if k not in vocab.MARK_TYPES or s not in vocab.CATEGORY_STATUS:
            raise ValueError("Situação de categoria inválida.")
    return v


def _check_range(lo, hi, label):
    if lo is not None and hi is not None and lo > hi:
        raise ValueError(f"{label}: mínimo maior que máximo.")


# ---------------------------------------------------------------- AM


class AmCaseIn(BaseModel):
    """Todos os campos são opcionais para permitir salvamento parcial (rascunho)."""

    family_name: str | None = Field(default=None, max_length=200)
    given_names: str | None = Field(default=None, max_length=200)
    sex: str | None = None
    date_of_birth: date | None = None
    age_years: int | None = Field(default=None, ge=0, le=130)
    height_min_cm: int | None = Field(default=None, ge=30, le=250)
    height_max_cm: int | None = Field(default=None, ge=30, le=250)
    weight_min_kg: int | None = Field(default=None, ge=1, le=400)
    weight_max_kg: int | None = Field(default=None, ge=1, le=400)
    build: str | None = None
    height_certainty: str | None = None
    category_status: dict[str, str] = Field(default_factory=dict)
    form_data: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.sex is not None and self.sex not in vocab.AM_SEX:
            raise ValueError("Sexo inválido.")
        if self.build is not None and self.build not in vocab.BUILD:
            raise ValueError("Compleição inválida (campo 416).")
        if self.status is not None and self.status not in vocab.AM_STATUS:
            raise ValueError("Status inválido.")
        if self.height_certainty is not None and self.height_certainty not in vocab.CERTAINTIES:
            raise ValueError("Grau de certeza inválido.")
        _check_range(self.height_min_cm, self.height_max_cm, "Estatura")
        _check_range(self.weight_min_kg, self.weight_max_kg, "Peso")
        _check_category_status(self.category_status)
        if self.date_of_birth and self.date_of_birth > date.today():
            raise ValueError("Data de nascimento no futuro.")
        return self


class AmCaseUpdate(AmCaseIn):
    expected_version: int


class InterviewIn(BaseModel):
    informant_name: str = Field(min_length=1, max_length=200)
    relationship_to_missing: str | None = Field(default=None, max_length=120)
    contact: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=1000)
    interview_date: date | None = None
    location: str | None = Field(default=None, max_length=200)
    is_point_of_contact: bool = False
    notes: str | None = Field(default=None, max_length=10000)


class InterviewOut(InterviewIn, ORM):
    id: uuid.UUID
    interviewer_id: uuid.UUID
    created_at: datetime


class AmCaseSummary(ORM):
    id: uuid.UUID
    am_number: str
    status: str
    family_name: str | None
    given_names: str | None
    sex: str | None
    age_years: int | None
    date_of_birth: date | None
    updated_at: datetime


class AmCaseOut(AmCaseSummary):
    operation_id: uuid.UUID
    origin_base_id: uuid.UUID
    height_min_cm: int | None
    height_max_cm: int | None
    weight_min_kg: int | None
    weight_max_kg: int | None
    build: str | None
    height_certainty: str | None
    category_status: dict
    form_data: dict
    version: int
    created_at: datetime
    created_by: uuid.UUID
    updated_by: uuid.UUID
    interviews: list[InterviewOut]
    marks: list[MarkOut]
    effects: list[EffectOut]


# ---------------------------------------------------------------- PM


class PmCaseIn(BaseModel):
    scene_ref: str | None = None  # só usado na criação (compõe o número PM)
    recovery_date: date | None = None
    recovery_place: str | None = Field(default=None, max_length=200)
    state_of_body: str | None = None
    sex: str | None = None
    sex_reason: str | None = Field(default=None, max_length=200)
    age_min_years: int | None = Field(default=None, ge=0, le=130)
    age_max_years: int | None = Field(default=None, ge=0, le=130)
    age_method: str | None = Field(default=None, max_length=200)
    height_min_cm: int | None = Field(default=None, ge=30, le=250)
    height_max_cm: int | None = Field(default=None, ge=30, le=250)
    weight_min_kg: int | None = Field(default=None, ge=1, le=400)
    weight_max_kg: int | None = Field(default=None, ge=1, le=400)
    build: str | None = None
    height_certainty: str | None = None
    category_status: dict[str, str] = Field(default_factory=dict)
    form_data: dict[str, Any] = Field(default_factory=dict)
    status: str | None = None

    @model_validator(mode="after")
    def _check(self):
        if self.sex is not None and self.sex not in vocab.PM_SEX:
            raise ValueError("Sexo inválido (campo 535).")
        if self.state_of_body is not None and self.state_of_body not in vocab.STATE_OF_BODY:
            raise ValueError("Estado do corpo inválido (campo 402).")
        if self.build is not None and self.build not in vocab.BUILD:
            raise ValueError("Compleição inválida (campo 416).")
        if self.status is not None and self.status not in vocab.PM_STATUS:
            raise ValueError("Status inválido.")
        if self.height_certainty is not None and self.height_certainty not in vocab.CERTAINTIES:
            raise ValueError("Grau de certeza inválido.")
        _check_range(self.age_min_years, self.age_max_years, "Idade estimada")
        _check_range(self.height_min_cm, self.height_max_cm, "Estatura")
        _check_range(self.weight_min_kg, self.weight_max_kg, "Peso")
        _check_category_status(self.category_status)
        return self


class PmCaseUpdate(PmCaseIn):
    expected_version: int


class CustodyIn(BaseModel):
    event_type: str
    occurred_at: datetime
    location: str | None = Field(default=None, max_length=200)
    responsible: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("event_type")
    @classmethod
    def _e(cls, v: str) -> str:
        if v not in vocab.CUSTODY_EVENTS:
            raise ValueError("Tipo de evento de custódia inválido.")
        return v


class CustodyOut(CustodyIn, ORM):
    id: uuid.UUID
    recorded_by: uuid.UUID
    recorded_at: datetime


class PmCaseSummary(ORM):
    id: uuid.UUID
    pm_number: str
    status: str
    state_of_body: str | None
    sex: str | None
    age_min_years: int | None
    age_max_years: int | None
    recovery_date: date | None
    updated_at: datetime


class PmCaseOut(PmCaseSummary):
    operation_id: uuid.UUID
    origin_base_id: uuid.UUID
    scene_ref: str | None
    recovery_place: str | None
    sex_reason: str | None
    age_method: str | None
    height_min_cm: int | None
    height_max_cm: int | None
    weight_min_kg: int | None
    weight_max_kg: int | None
    build: str | None
    height_certainty: str | None
    category_status: dict
    form_data: dict
    version: int
    created_at: datetime
    created_by: uuid.UUID
    updated_by: uuid.UUID
    marks: list[MarkOut]
    effects: list[EffectOut]
    custody: list[CustodyOut] = []


# ---------------------------------------------------------------- anexos


class AttachmentOut(ORM):
    id: uuid.UUID
    am_case_id: uuid.UUID | None
    pm_case_id: uuid.UUID | None
    base_id: uuid.UUID
    doc_type: str
    subject: str
    title: str
    description: str | None
    source: str | None
    evidence_ref: str | None
    obtained_at: datetime | None
    uploaded_at: datetime
    uploaded_by: uuid.UUID
    uploaded_by_name: str | None = None
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    page_count: int | None
    status: str
    version: int
    supersedes_id: uuid.UUID | None
    superseded: bool
    withdrawn_reason: str | None


class AttachmentMetaUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    source: str | None = Field(default=None, max_length=200)
    evidence_ref: str | None = Field(default=None, max_length=80)


class WithdrawIn(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)


# ---------------------------------------------------------------- reconciliação


class ReviewIn(BaseModel):
    status: str
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("status")
    @classmethod
    def _s(cls, v: str) -> str:
        allowed = {"SUGERIDO", "EM_ANALISE", "INFORMACOES_COMPLEMENTARES", "DESCARTADO",
                   "ENCAMINHADO_AVALIACAO_TECNICA"}
        if v not in allowed:
            raise ValueError("Status de revisão inválido. O sistema não registra identificação positiva.")
        return v
