import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import vocab
from app.config import get_settings
from app.db import get_db
from app.deps import Ctx, get_ctx
from app.models import AmCase, Attachment, PmCase, User
from app.routers import common
from app.schemas import AttachmentMetaUpdate, AttachmentOut, WithdrawIn
from app.services import audit, storage

router = APIRouter(prefix="/api/attachments", tags=["anexos"])

META_FIELDS = ["title", "description", "source", "evidence_ref"]


def _kind(att: Attachment) -> str:
    return "AM" if att.am_case_id else "PM"


def _check(db: Session, ctx: Ctx, kind: str, action: str, object_id=None) -> None:
    perm = f"att_{kind.lower()}:{action}"
    if not ctx.has(perm):
        audit.record(db, "ANEXO_ACESSO_NEGADO", ctx=ctx, object_type="attachment", object_id=object_id,
                     outcome="NEGADO", details={"permissao": perm})
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sem permissão para anexos deste tipo de registro.")


def _load(db: Session, ctx: Ctx, att_id: uuid.UUID, action: str) -> Attachment:
    att = db.get(Attachment, att_id)
    if att is None or att.operation_id != ctx.operation_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anexo não encontrado nesta operação.")
    _check(db, ctx, _kind(att), action, att.id)
    return att


def _out(db: Session, att: Attachment) -> AttachmentOut:
    out = AttachmentOut.model_validate(att)
    user = db.get(User, att.uploaded_by)
    out.uploaded_by_name = user.full_name if user else None
    return out


async def _read_limited(file: UploadFile) -> bytes:
    limit = get_settings().max_upload_bytes
    chunks, total = [], 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                f"Arquivo excede o limite de {get_settings().max_upload_mb} MB.")
        chunks.append(chunk)
    return b"".join(chunks)


def _validate_type(kind: str, doc_type: str, subject: str) -> None:
    types = vocab.ATTACHMENT_TYPES_AM if kind == "AM" else vocab.ATTACHMENT_TYPES_PM
    subjects = vocab.ATTACHMENT_SUBJECTS_AM if kind == "AM" else vocab.ATTACHMENT_SUBJECTS_PM
    if doc_type not in types:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Tipo de anexo '{doc_type}' não permitido para registros {kind}.")
    if subject not in subjects:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Vínculo '{subject}' inválido para registros {kind}.")


def _store_or_422(db: Session, ctx: Ctx, data: bytes, filename: str, case_id) -> storage.StoredFile:
    try:
        return storage.store(data, filename)
    except storage.InvalidFile as exc:
        audit.record(db, "ANEXO_REJEITADO", ctx=ctx, object_type="attachment", object_id=case_id,
                     outcome="REJEITADO", details={"arquivo": storage.safe_filename(filename),
                                                    "motivo": str(exc)})
        db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.post("", response_model=AttachmentOut, status_code=201)
async def upload(
    record_kind: str = Form(..., pattern="^(AM|PM)$"),
    case_id: uuid.UUID = Form(...),
    doc_type: str = Form(...),
    subject: str = Form(...),
    title: str = Form(..., min_length=1, max_length=200),
    description: str | None = Form(None, max_length=5000),
    source: str | None = Form(None, max_length=200),
    evidence_ref: str | None = Form(None, max_length=80),
    obtained_at: datetime | None = Form(None),
    file: UploadFile = File(...),
    ctx: Ctx = Depends(get_ctx),
    db: Session = Depends(get_db),
):
    _check(db, ctx, record_kind, "write", case_id)
    case = common.get_case(db, ctx, AmCase if record_kind == "AM" else PmCase, case_id)
    _validate_type(record_kind, doc_type, subject)
    data = await _read_limited(file)
    stored = _store_or_422(db, ctx, data, file.filename or "arquivo", case_id)
    att = Attachment(
        operation_id=ctx.operation_id, base_id=ctx.base_id,
        am_case_id=case.id if record_kind == "AM" else None,
        pm_case_id=case.id if record_kind == "PM" else None,
        doc_type=doc_type, subject=subject, title=title, description=description, source=source,
        evidence_ref=evidence_ref, obtained_at=obtained_at, uploaded_by=ctx.user.id,
        original_filename=(file.filename or "arquivo")[:255], safe_filename=stored.safe_filename,
        mime_type=stored.mime_type, size_bytes=stored.size_bytes, sha256=stored.sha256,
        storage_key=stored.storage_key, page_count=stored.page_count, status="ARMAZENADO",
    )
    db.add(att)
    db.flush()
    audit.record(db, "ANEXO_ENVIADO", ctx=ctx, object_type="attachment", object_id=att.id,
                 details={"registro": f"{record_kind}:{case.id}", "tipo": doc_type, "vinculo": subject,
                          "sha256": stored.sha256, "bytes": stored.size_bytes, "mime": stored.mime_type})
    db.commit()
    db.refresh(att)
    return _out(db, att)


@router.get("", response_model=list[AttachmentOut])
def list_attachments(
    am_case_id: uuid.UUID | None = None,
    pm_case_id: uuid.UUID | None = None,
    doc_type: str | None = None,
    include_superseded: bool = Query(False),
    ctx: Ctx = Depends(get_ctx),
    db: Session = Depends(get_db),
):
    if (am_case_id is None) == (pm_case_id is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe am_case_id ou pm_case_id.")
    kind = "AM" if am_case_id else "PM"
    _check(db, ctx, kind, "read")
    case = common.get_case(db, ctx, AmCase if kind == "AM" else PmCase, am_case_id or pm_case_id)
    stmt = select(Attachment).where(
        (Attachment.am_case_id if kind == "AM" else Attachment.pm_case_id) == case.id)
    if doc_type:
        stmt = stmt.where(Attachment.doc_type == doc_type)
    if not include_superseded:
        stmt = stmt.where(Attachment.superseded.is_(False))
    return [_out(db, a) for a in db.scalars(stmt.order_by(Attachment.uploaded_at))]


@router.get("/{att_id}", response_model=AttachmentOut)
def get_meta(att_id: uuid.UUID, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    return _out(db, _load(db, ctx, att_id, "read"))


def _file_response(data: bytes, mime: str, filename: str, inline: bool) -> Response:
    disp = "inline" if inline else "attachment"
    return Response(
        content=data, media_type=mime,
        headers={
            "Content-Disposition": f'{disp}; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'",
        },
    )


@router.get("/{att_id}/content")
def content(att_id: uuid.UUID, download: bool = False, ctx: Ctx = Depends(get_ctx),
            db: Session = Depends(get_db)):
    """Imagens são entregues sem metadados EXIF/GPS. O original permanece intacto no armazenamento."""
    att = _load(db, ctx, att_id, "read")
    try:
        raw = storage.read_bytes(att.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Arquivo ausente no armazenamento.") from exc
    data = storage.sanitized_image(raw, att.mime_type) if att.mime_type.startswith("image/") else raw
    audit.record(db, "ANEXO_DOWNLOAD" if download else "ANEXO_VISUALIZADO", ctx=ctx,
                 object_type="attachment", object_id=att.id)
    db.commit()
    return _file_response(data, att.mime_type, att.safe_filename, inline=not download)


@router.get("/{att_id}/thumbnail")
def thumbnail(att_id: uuid.UUID, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    att = _load(db, ctx, att_id, "read")
    if not att.mime_type.startswith("image/"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Miniatura disponível apenas para imagens.")
    data = storage.sanitized_image(storage.read_bytes(att.storage_key), att.mime_type, max_side=320)
    return _file_response(data, att.mime_type, "miniatura-" + att.safe_filename, inline=True)


@router.get("/{att_id}/verify")
def verify(att_id: uuid.UUID, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    att = _load(db, ctx, att_id, "read")
    try:
        current = storage.sha256_of(att.storage_key)
    except FileNotFoundError:
        current = None
    ok = current == att.sha256
    audit.record(db, "ANEXO_INTEGRIDADE_VERIFICADA", ctx=ctx, object_type="attachment", object_id=att.id,
                 outcome="SUCESSO" if ok else "FALHA", details={"esperado": att.sha256, "atual": current})
    db.commit()
    return {"ok": ok, "sha256_registrado": att.sha256, "sha256_atual": current}


@router.patch("/{att_id}", response_model=AttachmentOut)
def update_meta(att_id: uuid.UUID, body: AttachmentMetaUpdate, ctx: Ctx = Depends(get_ctx),
                db: Session = Depends(get_db)):
    att = _load(db, ctx, att_id, "write")
    before = common.snapshot(att, META_FIELDS)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(att, k, v)
    audit.record(db, "ANEXO_METADADOS_ALTERADOS", ctx=ctx, object_type="attachment", object_id=att.id,
                 details=audit.diff(before, common.snapshot(att, META_FIELDS)))
    db.commit()
    db.refresh(att)
    return _out(db, att)


@router.post("/{att_id}/versions", response_model=AttachmentOut, status_code=201)
async def new_version(att_id: uuid.UUID, file: UploadFile = File(...), ctx: Ctx = Depends(get_ctx),
                      db: Session = Depends(get_db)):
    """Substituição por nova versão: o original continua armazenado e consultável."""
    old = _load(db, ctx, att_id, "write")
    if old.superseded or old.status != "ARMAZENADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "Somente a versão vigente pode ser substituída.")
    data = await _read_limited(file)
    stored = _store_or_422(db, ctx, data, file.filename or "arquivo", old.id)
    att = Attachment(
        operation_id=old.operation_id, base_id=ctx.base_id, am_case_id=old.am_case_id,
        pm_case_id=old.pm_case_id, doc_type=old.doc_type, subject=old.subject, title=old.title,
        description=old.description, source=old.source, evidence_ref=old.evidence_ref,
        obtained_at=old.obtained_at, uploaded_by=ctx.user.id,
        original_filename=(file.filename or "arquivo")[:255], safe_filename=stored.safe_filename,
        mime_type=stored.mime_type, size_bytes=stored.size_bytes, sha256=stored.sha256,
        storage_key=stored.storage_key, page_count=stored.page_count, version=old.version + 1,
        supersedes_id=old.id,
    )
    old.superseded = True
    db.add(att)
    db.flush()
    audit.record(db, "ANEXO_NOVA_VERSAO", ctx=ctx, object_type="attachment", object_id=att.id,
                 details={"substitui": old.id, "versao": att.version, "sha256": stored.sha256})
    db.commit()
    db.refresh(att)
    return _out(db, att)


@router.post("/{att_id}/withdraw", response_model=AttachmentOut)
def withdraw(att_id: uuid.UUID, body: WithdrawIn, ctx: Ctx = Depends(get_ctx), db: Session = Depends(get_db)):
    """Retira o anexo de uso, com justificativa. O arquivo NÃO é apagado."""
    att = _load(db, ctx, att_id, "write")
    if att.status == "RETIRADO":
        raise HTTPException(status.HTTP_409_CONFLICT, "Anexo já retirado.")
    att.status = "RETIRADO"
    att.withdrawn_reason = body.reason
    audit.record(db, "ANEXO_RETIRADO", ctx=ctx, object_type="attachment", object_id=att.id,
                 details={"motivo": body.reason})
    db.commit()
    db.refresh(att)
    return _out(db, att)
