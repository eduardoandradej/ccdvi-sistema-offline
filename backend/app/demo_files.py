"""Gera arquivos INTEIRAMENTE SINTÉTICOS para demonstração e testes (sem identidade real).

Todas as imagens/PDFs contêm a marca d'água "TESTE — DADO FICTÍCIO".
"""

import io

from PIL import Image, ImageDraw, ImageFont

WATERMARK = "TESTE — DADO FICTÍCIO"


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow sem FreeType
        return ImageFont.load_default()


def _canvas(w: int, h: int, bg: tuple[int, int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    for y in range(0, h, 120):  # marca d'água repetida
        draw.text((20, y + 40), WATERMARK, fill=(200, 60, 60), font=_font(28))
    return img, draw


def reference_photo(label: str = "Pessoa fictícia") -> bytes:
    """Silhueta genérica (não é rosto real) — 'fotografia de referência' AM."""
    img, d = _canvas(600, 800, (225, 232, 240))
    d.ellipse((220, 140, 380, 320), fill=(150, 160, 175))
    d.rounded_rectangle((150, 330, 450, 760), radius=60, fill=(150, 160, 175))
    d.text((30, 720), label, fill=(20, 20, 20), font=_font(30))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


def object_photo(label: str = "Objeto fictício") -> bytes:
    """Imagem genérica de vestimenta/objeto (PM) — sem conteúdo cadavérico."""
    img, d = _canvas(800, 600, (240, 236, 225))
    d.rectangle((250, 150, 550, 450), outline=(60, 60, 120), width=8)
    d.line((250, 150, 550, 450), fill=(60, 60, 120), width=4)
    d.text((30, 540), label, fill=(20, 20, 20), font=_font(30))
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def id_document_pdf(name: str = "FULANA DE TAL FICTÍCIA", number: str = "000.000.000-00") -> bytes:
    """Documento de identificação fictício, em PDF de 2 páginas (frente/verso)."""
    pages = []
    for side in ("FRENTE", "VERSO"):
        img, d = _canvas(1240, 800, (235, 245, 235))
        d.text((60, 60), f"DOCUMENTO DE IDENTIDADE FICTÍCIO — {side}", fill=(0, 0, 0), font=_font(40))
        d.text((60, 200), f"Nome: {name}", fill=(0, 0, 0), font=_font(36))
        d.text((60, 260), f"Número: {number}", fill=(0, 0, 0), font=_font(36))
        d.text((60, 320), "Emitido por: ÓRGÃO FICTÍCIO DE TESTE", fill=(0, 0, 0), font=_font(36))
        pages.append(img)
    out = io.BytesIO()
    pages[0].save(out, format="PDF", save_all=True, append_images=pages[1:], resolution=150)
    return out.getvalue()


def dental_record_pdf() -> bytes:
    img, d = _canvas(1240, 1754, (255, 255, 255))
    d.text((60, 60), "PRONTUÁRIO ODONTOLÓGICO FICTÍCIO", fill=(0, 0, 0), font=_font(44))
    d.text((60, 160), "Clínica Odontológica Fictícia — documento de teste", fill=(0, 0, 0), font=_font(32))
    d.text((60, 240), "Dente 16: restauração (coroa) — dado sintético", fill=(0, 0, 0), font=_font(32))
    d.text((60, 300), "Dente 36: ausente — dado sintético", fill=(0, 0, 0), font=_font(32))
    out = io.BytesIO()
    img.save(out, format="PDF", resolution=150)
    return out.getvalue()


def jpeg_with_gps_exif() -> bytes:
    """Imagem sintética com EXIF contendo GPS fictício, para testar a remoção de metadados."""
    img, _ = _canvas(320, 240, (200, 220, 240))
    exif = Image.Exif()
    exif[0x010F] = "FabricanteFicticio"  # Make
    gps = {1: "S", 2: (23.0, 33.0, 0.0), 3: "W", 4: (46.0, 38.0, 0.0)}
    exif[0x8825] = gps
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif.tobytes())
    return out.getvalue()
