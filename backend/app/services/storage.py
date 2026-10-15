"""Armazenamento de anexos em diretório privado (fora do webroot).

- O conteúdo é validado pelos bytes (assinatura + decodificação), não pela extensão.
- O original é preservado byte a byte, identificado por UUID, com SHA-256 registrado.
- Visualizações/downloads de imagens são reprocessados sem metadados EXIF/GPS.
"""

import hashlib
import io
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.config import get_settings

ALLOWED = {
    "image/jpeg": (b"\xff\xd8\xff", {".jpg", ".jpeg"}),
    "image/png": (b"\x89PNG\r\n\x1a\n", {".png"}),
    "application/pdf": (b"%PDF-", {".pdf"}),
}
Image.MAX_IMAGE_PIXELS = 80_000_000  # proteção contra "bombas" de descompressão


class InvalidFile(ValueError):
    pass


@dataclass
class StoredFile:
    storage_key: str
    sha256: str
    size_bytes: int
    mime_type: str
    safe_filename: str
    page_count: int | None


def safe_filename(name: str) -> str:
    name = os.path.basename(name.replace("\\", "/"))
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return (name or "arquivo")[:120]


def detect_and_validate(data: bytes, filename: str) -> tuple[str, int | None]:
    if not data:
        raise InvalidFile("Arquivo vazio.")
    mime = next((m for m, (magic, _) in ALLOWED.items() if data.startswith(magic)), None)
    if mime is None:
        raise InvalidFile("Tipo de arquivo não permitido. Use JPEG, PNG ou PDF.")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED[mime][1]:
        raise InvalidFile(
            f"A extensão '{ext or '(nenhuma)'}' não corresponde ao conteúdo real do arquivo ({mime})."
        )
    if mime.startswith("image/"):
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
            with Image.open(io.BytesIO(data)) as img:
                img.load()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise InvalidFile("Imagem corrompida ou inválida.") from exc
        return mime, None
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise InvalidFile("PDF protegido por senha não é aceito.")
        pages = len(reader.pages)
    except (PdfReadError, ValueError, KeyError, OSError) as exc:
        raise InvalidFile("PDF corrompido ou inválido.") from exc
    if pages < 1:
        raise InvalidFile("PDF sem páginas.")
    return mime, pages


def storage_root() -> Path:
    root = get_settings().storage_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def path_for(storage_key: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f-]{36}", storage_key):
        raise InvalidFile("Chave de armazenamento inválida.")
    return storage_root() / storage_key


def store(data: bytes, filename: str) -> StoredFile:
    mime, pages = detect_and_validate(data, filename)
    file_id = str(uuid.uuid4())
    key = f"{file_id[:2]}/{file_id[2:4]}/{file_id}"
    target = path_for(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    with open(tmp, "wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
    os.chmod(target, 0o440)
    digest = hashlib.sha256(data).hexdigest()
    # Confirma a persistência relendo do disco antes de declarar sucesso
    if sha256_of(key) != digest:
        target.unlink(missing_ok=True)
        raise OSError("Falha de integridade ao gravar o arquivo.")
    return StoredFile(key, digest, len(data), mime, safe_filename(filename), pages)


def sha256_of(storage_key: str) -> str:
    h = hashlib.sha256()
    with open(path_for(storage_key), "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_bytes(storage_key: str) -> bytes:
    return path_for(storage_key).read_bytes()


def sanitized_image(data: bytes, mime: str, max_side: int | None = None) -> bytes:
    """Reprocessa a imagem descartando EXIF/GPS e demais metadados."""
    with Image.open(io.BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)
        if max_side:
            img.thumbnail((max_side, max_side))
        out = io.BytesIO()
        if mime == "image/png":
            img.save(out, format="PNG")
        else:
            img.convert("RGB").save(out, format="JPEG", quality=90)
        return out.getvalue()
