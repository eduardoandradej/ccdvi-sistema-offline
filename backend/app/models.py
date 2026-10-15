"""Modelo de dados do Sistema DVI Offline.

Convenções:
- Todas as entidades operacionais usam UUID (gerado pela aplicação) para permitir, no futuro,
  consolidação entre instalações independentes (uma por base) sem colisão de chaves.
- Códigos de campo "INTERPOL" referem-se aos números dos formulários AM/PM 2023 (ex.: 404, 408).
- Dados de formulário não usados pelo motor de comparação ficam em `form_data` (JSONB),
  organizados por seção (aba); campos comparáveis ficam em colunas/tabelas próprias.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------- acesso / contexto


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    job_title: Mapped[str | None] = mapped_column(String(120))  # cargo
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    authorizations: Mapped[list["Authorization"]] = relationship(back_populates="user")


class Operation(TimestampMixin, Base):
    __tablename__ = "operations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # TREINAMENTO | REAL
    status: Mapped[str] = mapped_column(String(20), default="ATIVA")  # ATIVA | ENCERRADA
    # Anexo 9: código telefônico do país usado na numeração AM/PM (ex.: 55 = Brasil)
    country_code: Mapped[str] = mapped_column(String(4), default="55")
    disaster_place: Mapped[str | None] = mapped_column(String(200))
    disaster_nature: Mapped[str | None] = mapped_column(String(200))
    disaster_date: Mapped[date | None] = mapped_column(Date)

    __table_args__ = (
        CheckConstraint("kind in ('TREINAMENTO','REAL')", name="ck_operation_kind"),
        CheckConstraint("status in ('ATIVA','ENCERRADA')", name="ck_operation_status"),
    )


class OperationalBase(TimestampMixin, Base):
    """Local/posto físico de trabalho. Não é papel de segurança."""

    __tablename__ = "bases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"))
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))  # COMANDO | AM | PM | OUTRO

    __table_args__ = (
        UniqueConstraint("operation_id", "code", name="uq_base_operation_code"),
        CheckConstraint("kind in ('COMANDO','AM','PM','OUTRO')", name="ck_base_kind"),
    )


class Authorization(TimestampMixin, Base):
    """Concede a um usuário uma função em uma base de uma operação."""

    __tablename__ = "authorizations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"))
    base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bases.id"))
    role: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="authorizations")
    operation: Mapped[Operation] = relationship()
    base: Mapped[OperationalBase] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "operation_id", "base_id", "role", name="uq_authorization"),
    )


class UserSession(Base):
    """Sessão de servidor. O cookie contém apenas um token aleatório; aqui guardamos o hash."""

    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    # contexto ativo (validado no servidor a cada requisição)
    operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operations.id"))
    base_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bases.id"))
    role: Mapped[str | None] = mapped_column(String(40))

    user: Mapped[User] = relationship()


class NumberCounter(Base):
    """Sequência de numeração AM/PM por operação (Anexo 9), com bloqueio de linha."""

    __tablename__ = "number_counters"
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(2), primary_key=True)  # AM | PM
    last_value: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------- Ante Mortem


class AmCase(TimestampMixin, Base):
    __tablename__ = "am_cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"), index=True)
    origin_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bases.id"))
    am_number: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="RASCUNHO")
    # Cabeçalho do formulário AM
    family_name: Mapped[str | None] = mapped_column(String(200))
    given_names: Mapped[str | None] = mapped_column(String(200))
    sex: Mapped[str | None] = mapped_column(String(1))  # M F O U  (Male/Female/Other/Unknown)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    age_years: Mapped[int | None] = mapped_column(Integer)
    # 408 / 412 / 416 — valores informados (relato), com mínimo e máximo
    height_min_cm: Mapped[int | None] = mapped_column(Integer)
    height_max_cm: Mapped[int | None] = mapped_column(Integer)
    weight_min_kg: Mapped[int | None] = mapped_column(Integer)
    weight_max_kg: Mapped[int | None] = mapped_column(Integer)
    build: Mapped[str | None] = mapped_column(String(10))  # 1 slight / 2 medium / 3 large
    height_certainty: Mapped[str | None] = mapped_column(String(20))
    # Situação declarada por categoria (ex.: {"3": "NEGATIVO"} = família afirma não haver tatuagens)
    category_status: Mapped[dict] = mapped_column(JSONB, default=dict)
    form_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)

    interviews: Mapped[list["AmInterview"]] = relationship(
        back_populates="am_case", order_by="AmInterview.interview_date"
    )
    marks: Mapped[list["PhysicalMark"]] = relationship(
        primaryjoin="AmCase.id==PhysicalMark.am_case_id", viewonly=True
    )
    effects: Mapped[list["Effect"]] = relationship(
        primaryjoin="AmCase.id==Effect.am_case_id", viewonly=True
    )

    __table_args__ = (
        UniqueConstraint("operation_id", "am_number", name="uq_am_number"),
        CheckConstraint("sex is null or sex in ('M','F','O','U')", name="ck_am_sex"),
    )


class AmInterview(TimestampMixin, Base):
    """Entrevista/fonte (campo 105 'Information given by' e 110 'Point of contact')."""

    __tablename__ = "am_interviews"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    am_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("am_cases.id"), index=True)
    informant_name: Mapped[str] = mapped_column(String(200))
    relationship_to_missing: Mapped[str | None] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    interview_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(200))
    is_point_of_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    interviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    am_case: Mapped[AmCase] = relationship(back_populates="interviews")


# ---------------------------------------------------------------- Post Mortem


class PmCase(TimestampMixin, Base):
    __tablename__ = "pm_cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"), index=True)
    origin_base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bases.id"))
    pm_number: Mapped[str] = mapped_column(String(60))
    scene_ref: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="RASCUNHO")
    recovery_date: Mapped[date | None] = mapped_column(Date)
    recovery_place: Mapped[str | None] = mapped_column(String(200))
    state_of_body: Mapped[str | None] = mapped_column(String(20))  # 402: COMPLETO|INCOMPLETO|SEGMENTO
    sex: Mapped[str | None] = mapped_column(String(1))  # 535: M F I (indeterminado)
    sex_reason: Mapped[str | None] = mapped_column(String(200))
    age_min_years: Mapped[int | None] = mapped_column(Integer)  # 540
    age_max_years: Mapped[int | None] = mapped_column(Integer)
    age_method: Mapped[str | None] = mapped_column(String(200))
    height_min_cm: Mapped[int | None] = mapped_column(Integer)  # 408
    height_max_cm: Mapped[int | None] = mapped_column(Integer)
    weight_min_kg: Mapped[int | None] = mapped_column(Integer)
    weight_max_kg: Mapped[int | None] = mapped_column(Integer)
    build: Mapped[str | None] = mapped_column(String(10))
    height_certainty: Mapped[str | None] = mapped_column(String(20))
    category_status: Mapped[dict] = mapped_column(JSONB, default=dict)
    form_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)

    marks: Mapped[list["PhysicalMark"]] = relationship(
        primaryjoin="PmCase.id==PhysicalMark.pm_case_id", viewonly=True
    )
    effects: Mapped[list["Effect"]] = relationship(
        primaryjoin="PmCase.id==Effect.pm_case_id", viewonly=True
    )

    __table_args__ = (
        UniqueConstraint("operation_id", "pm_number", name="uq_pm_number"),
        CheckConstraint("sex is null or sex in ('M','F','I')", name="ck_pm_sex"),
    )


class CustodyEvent(Base):
    """Cadeia de custódia do registro PM (extensão do sistema, cf. Guia DVI cap. PM)."""

    __tablename__ = "custody_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    pm_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pm_cases.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(200))
    responsible: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------- itens comparáveis (AM e PM)


class PhysicalMark(TimestampMixin, Base):
    """Campo 404 — sinais particulares: tipo (1..6) × região anatômica (01..37)."""

    __tablename__ = "physical_marks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    am_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("am_cases.id"), index=True)
    pm_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pm_cases.id"), index=True)
    mark_type: Mapped[str] = mapped_column(String(2))
    region: Mapped[str] = mapped_column(String(2))
    description: Mapped[str | None] = mapped_column(Text)
    certainty: Mapped[str] = mapped_column(String(20))
    source: Mapped[str | None] = mapped_column(String(200))

    __table_args__ = (
        CheckConstraint("(am_case_id is null) <> (pm_case_id is null)", name="ck_mark_owner"),
    )


class Effect(TimestampMixin, Base):
    """Campos 300–350 (vestimentas, calçados, relógio, óculos, joias, documentos, objetos,
    eletrônicos) e 515 (implantes com número de série)."""

    __tablename__ = "effects"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    am_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("am_cases.id"), index=True)
    pm_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pm_cases.id"), index=True)
    field_code: Mapped[str] = mapped_column(String(3))
    item_code: Mapped[str] = mapped_column(String(3))
    type_style: Mapped[str | None] = mapped_column(String(200))
    colour: Mapped[str | None] = mapped_column(String(30))
    brand: Mapped[str | None] = mapped_column(String(120))
    material: Mapped[str | None] = mapped_column(String(120))
    size: Mapped[str | None] = mapped_column(String(40))
    inscription: Mapped[str | None] = mapped_column(String(200))
    where_worn: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    certainty: Mapped[str] = mapped_column(String(20))

    __table_args__ = (
        CheckConstraint("(am_case_id is null) <> (pm_case_id is null)", name="ck_effect_owner"),
    )


# ---------------------------------------------------------------- anexos


class Attachment(Base):
    __tablename__ = "attachments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"), index=True)
    base_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bases.id"))
    am_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("am_cases.id"), index=True)
    pm_case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pm_cases.id"), index=True)
    doc_type: Mapped[str] = mapped_column(String(40))
    subject: Mapped[str] = mapped_column(String(30))  # DESAPARECIDO | ENTREVISTADO | REGISTRO_PM
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(200))
    evidence_ref: Mapped[str | None] = mapped_column(String(80))
    obtained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    original_filename: Mapped[str] = mapped_column(String(255))
    safe_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(60))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    page_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="ARMAZENADO")
    # Versionamento: nunca sobrescrever original; nova versão aponta para a anterior
    version: Mapped[int] = mapped_column(Integer, default=1)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("attachments.id"))
    superseded: Mapped[bool] = mapped_column(Boolean, default=False)
    withdrawn_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("(am_case_id is null) <> (pm_case_id is null)", name="ck_attachment_owner"),
        CheckConstraint(
            "status in ('ARMAZENADO','RETIRADO','ERRO')", name="ck_attachment_status"
        ),
    )


# ---------------------------------------------------------------- reconciliação


class MatchReview(TimestampMixin, Base):
    """Registro de análise humana de um par candidato AM×PM. Nunca representa identificação."""

    __tablename__ = "match_reviews"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    operation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("operations.id"), index=True)
    am_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("am_cases.id"))
    pm_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pm_cases.id"))
    status: Mapped[str] = mapped_column(String(40), default="SUGERIDO")
    notes: Mapped[str | None] = mapped_column(Text)
    algorithm_version: Mapped[str] = mapped_column(String(20))
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    result_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    technical_index: Mapped[float | None] = mapped_column()
    reviewed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("am_case_id", "pm_case_id", name="uq_match_pair"),
        CheckConstraint(
            "status in ('SUGERIDO','EM_ANALISE','INFORMACOES_COMPLEMENTARES','DESCARTADO',"
            "'ENCAMINHADO_AVALIACAO_TECNICA')",
            name="ck_match_status",
        ),
    )


# ---------------------------------------------------------------- auditoria


class AuditEvent(Base):
    """Trilha de auditoria somente-inserção (um gatilho no banco bloqueia UPDATE/DELETE)."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    username: Mapped[str | None] = mapped_column(String(64))
    operation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operations.id"))
    base_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bases.id"))
    role: Mapped[str | None] = mapped_column(String(40))
    action: Mapped[str] = mapped_column(String(60), index=True)
    object_type: Mapped[str | None] = mapped_column(String(40))
    object_id: Mapped[str | None] = mapped_column(String(64), index=True)
    outcome: Mapped[str] = mapped_column(String(20), default="SUCESSO")
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    client_ip: Mapped[str | None] = mapped_column(String(64))
