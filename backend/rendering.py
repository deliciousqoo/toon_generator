"""Deterministic, visibly synthetic PNGs for the local mock-only pipeline.

These drawings exercise storyboard, candidate selection, and asset storage. They
are not outputs of an image model and intentionally ignore reference artwork.
"""

from __future__ import annotations

import hashlib
import io
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

PAPER = "#FCF9F2"
INK = "#253C3E"
TEAL = "#3D8078"
CORAL = "#D77760"
PALE_TEAL = "#E5EFEB"
PALE_CORAL = "#F7E8DF"


@lru_cache(maxsize=24)
def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """Prefer Korean-capable local fonts, without downloading anything."""
    fonts = [
        Path("C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf" if bold else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in fonts:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow older than 10.1
        return ImageFont.load_default()


def _string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return _string(value.get("text", value.get("dialogue", "")))
    if isinstance(value, (list, tuple)):
        return " / ".join(filter(None, (_string(item) for item in value)))
    return str(value).strip()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont,
          width: int, limit: int) -> list[str]:
    """Wrap by measured glyph width, including Korean and long unbroken words."""
    text = text.replace("\r", "").strip()
    if not text:
        return []
    lines: list[str] = []
    current = ""
    for character in text:
        if character == "\n":
            lines.append(current.rstrip())
            current = ""
        elif current and draw.textlength(current + character, font=font) > width:
            lines.append(current.rstrip())
            current = character.lstrip()
        else:
            current += character
    if current:
        lines.append(current.rstrip())
    if len(lines) > limit:
        lines = lines[:limit]
        while lines[-1] and draw.textlength(lines[-1] + "…", font=font) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines


def _text_block(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int],
                width: int, size: int, limit: int, *, fill: str = INK,
                bold: bool = False, spacing: int = 6) -> None:
    font = _font(size, bold)
    for index, line in enumerate(_wrap(draw, text, font, width, limit)):
        draw.text((xy[0], xy[1] + index * (size + spacing)), line, font=font, fill=fill)


def _png(image: Image.Image, **metadata: str) -> bytes:
    info = PngImagePlugin.PngInfo()
    info.add_text("generator", "toon-studio-local-mock-v1")
    info.add_text("synthetic", "true")
    for key, value in metadata.items():
        info.add_text(key, value)
    output = io.BytesIO()
    image.save(output, format="PNG", pnginfo=info, optimize=True)
    return output.getvalue()


def _protagonist(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float,
                 pose: int, rough: bool, identity: str) -> None:
    """A simple recurring invented figure: teal sweater, soft square head, tuft."""
    def box(a: int, b: int, c: int, d: int) -> tuple[float, float, float, float]:
        return (x + a * scale, y + b * scale, x + c * scale, y + d * scale)

    def line(points: list[tuple[int, int]], color: str = INK, width: int = 4) -> None:
        draw.line([(x + a * scale, y + b * scale) for a, b in points],
                  fill=color, width=max(1, round(width * scale)), joint="curve")

    stroke = max(1, round((2 if rough else 3) * scale))
    outfit = PAPER if rough else TEAL
    draw.ellipse(box(-65, 148, 69, 167), fill="#E4E3D9")
    line([(-19, 123), (-20, 151), (-34, 153)])
    line([(21, 123), (22, 151), (37, 153)])
    draw.rounded_rectangle(box(-44, 35, 44, 126), radius=18 * scale,
                           fill=outfit, outline=INK, width=stroke)
    if not rough:
        draw.rectangle(box(-8, 94, 8, 108), fill="#A3CEC0")
    if pose == 0:
        line([(-40, 53), (-62, 82), (-81, 69)])
        line([(40, 53), (67, 78), (82, 49)])
    elif pose == 1:
        line([(-40, 55), (-60, 20), (-84, 9)])
        line([(40, 55), (71, 31), (83, -5)])
    elif pose == 2:
        line([(-40, 57), (-65, 96), (-30, 103)])
        line([(40, 57), (72, 93), (38, 103)])
    else:
        line([(-40, 55), (-65, 70), (-90, 54)])
        line([(40, 55), (64, 39), (81, 33)])
    draw.rounded_rectangle(box(-54, -70, 54, 41), radius=41 * scale,
                           fill=PAPER if rough else "#FFFDF8", outline=INK, width=stroke)
    seed = hashlib.sha256(identity.encode("utf-8")).digest()[0]
    tuft = -8 if seed % 2 else 7
    line([(tuft - 14, -69), (tuft - 2, -84), (tuft + 12, -74)], width=3)
    for eye in (-19, 19):
        draw.ellipse(box(eye - 3, -23, eye + 3, -15), fill=INK)
    if pose == 1:
        draw.ellipse(box(-6, -1, 6, 11), outline=INK, width=stroke)
    else:
        draw.arc(box(-12, -12, 12, 12), 15, 165, fill=INK, width=stroke)
    if not rough:
        draw.ellipse(box(-37, -2, -23, 6), fill="#EFC0A6")
        draw.ellipse(box(23, -2, 37, 6), fill="#EFC0A6")


def render_cut(unit: dict, *, variant: int = 0, rough: bool = False,
               character: dict | None = None) -> bytes:
    """Draw one Level 1 thumbnail (480×400) or mock candidate (640×640).

    ``variant`` deterministically changes composition and pose. Character
    identity stays stable across units and variants. Text is retained in PNG
    metadata as well as compact captions, so truncation never loses the source.
    """
    if not isinstance(unit, dict):
        raise TypeError("unit must be a dictionary")
    if not isinstance(variant, int) or variant < 0:
        raise ValueError("variant must be a nonnegative integer")
    try:
        order = max(1, int(unit.get("order", 1)))
    except (TypeError, ValueError):
        order = 1
    unit_id = _string(unit.get("unit_id")) or f"cut-{order:02d}"
    identity = _string((character or {}).get("character_id")) or _string(unit.get("character_id")) or "synthetic-protagonist"
    action = _string(unit.get("action")) or "가상의 장면 설명"
    dialogue = _string(unit.get("dialogue"))
    width, height = (480, 400) if rough else (640, 640)
    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    inset = 20 if rough else 26
    draw.rounded_rectangle((inset, inset, width - inset, height - inset),
                           radius=16, fill=PAPER, outline="#D7DED3", width=1)
    draw.rounded_rectangle((inset + 15, inset + 14, inset + 94, inset + 43),
                           radius=14, fill=TEAL)
    draw.text((inset + 28, inset + 17), f"CUT {order:02d}", font=_font(15, True), fill=PAPER)
    label = "SYNTHETIC / MOCK"
    draw.text((width - inset - 177, inset + 19), label, font=_font(14, True), fill=CORAL)
    if rough:
        draw.line((inset + 15, 75, width - inset - 15, 75), fill="#D7DED3", width=1)
        _protagonist(draw, width // 2 + (22 if variant % 2 else -18), 168,
                     0.63, (order - 1 + variant) % 4, True, identity)
        draw.line((67, 279, width - 67, 279), fill="#C8CEC5", width=2)
        draw.ellipse((358, 216, 381, 239), outline=CORAL, width=2)
        draw.line((371, 239, 371, 267), fill=CORAL, width=2)
        _text_block(draw, action, (inset + 15, 300), width - 2 * inset - 30, 17, 2)
        draw.text((inset + 15, 363), "LEVEL 1 · BEAT THUMBNAIL", font=_font(11), fill=TEAL)
    else:
        scene = (inset + 15, 85, width - inset - 15, 467)
        draw.rounded_rectangle(scene, radius=18, fill=PALE_CORAL if variant % 2 else PALE_TEAL)
        draw.rounded_rectangle((68, 122, 197, 276), radius=55, fill=PAPER)
        draw.line((132, 126, 132, 274), fill="#D7DED3", width=2)
        draw.line((74, 200, 190, 200), fill="#D7DED3", width=2)
        figure_x = 344 if variant % 2 else 274
        _protagonist(draw, figure_x, 281, 0.93, (order - 1 + variant) % 4, False, identity)
        draw.line((82, 436, 558, 436), fill="#B8CCC1", width=2)
        # Original, neutral scene props provide visual differences between variants.
        prop_x = 152 if variant % 2 else 479
        draw.rounded_rectangle((prop_x - 33, 369, prop_x + 31, 415), radius=7, fill=PAPER, outline=INK, width=2)
        draw.arc((prop_x + 20, 377, prop_x + 48, 407), 270, 90, fill=INK, width=2)
        draw.line((prop_x - 37, 418, prop_x + 38, 418), fill=CORAL, width=3)
        if dialogue:
            bubble_x = 238 if variant % 2 else 257
            draw.rounded_rectangle((bubble_x, 113, 578, 190), radius=19, fill="#FFFDF8", outline="#CAD5C9", width=1)
            draw.polygon([(bubble_x + 24, 188), (bubble_x + 12, 208), (bubble_x + 47, 188)], fill="#FFFDF8")
            _text_block(draw, dialogue, (bubble_x + 17, 126), 578 - bubble_x - 34, 19, 2)
        _text_block(draw, action, (inset + 20, 490), width - 2 * inset - 40, 22, 3, bold=True)
        draw.line((inset + 20, 581, width - inset - 20, 581), fill="#D7DED3", width=1)
        draw.text((inset + 20, 589), "MOCK DRAFT · " + ("A" if variant % 2 == 0 else "B"), font=_font(12, True), fill=TEAL)
        draw.text((width - inset - 192, 589), "HUMAN REVIEW REQUIRED", font=_font(11), fill="#737C6F")
    return _png(image, unit_id=unit_id, order=str(order), character_id=identity,
                action=action, dialogue=dialogue,
                composition=_string(unit.get("composition")),
                continuity=_string(unit.get("continuity")),
                variant=str(variant), rough=str(rough).lower())


def compose_preview(images: list[bytes]) -> bytes:
    """Compose all supplied cuts, in caller order, into a labeled review sheet."""
    if not images:
        raise ValueError("An episode preview requires at least one cut")
    if len(images) > 64:
        raise ValueError("An episode preview supports at most 64 cuts")
    decoded: list[Image.Image] = []
    unit_ids: list[str] = []
    for index, blob in enumerate(images):
        try:
            with Image.open(io.BytesIO(blob)) as image:
                if image.width > 4096 or image.height > 4096:
                    raise ValueError("A cut exceeds the preview image limit")
                image.load()
                unit_ids.append(image.info.get("unit_id", f"cut-{index + 1:02d}"))
                decoded.append(image.convert("RGB"))
        except (OSError, TypeError) as error:
            raise ValueError("Preview input must contain readable image bytes") from error
    columns = 1 if len(decoded) == 1 else 2
    rows = math.ceil(len(decoded) / columns)
    cell_width, cell_height, gap, header = 440, 440, 20, 82
    canvas = Image.new("RGB", (gap + columns * (cell_width + gap),
                               header + gap + rows * (cell_height + gap)), PAPER)
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 17), "EPISODE PREVIEW", font=_font(22, True), fill=INK)
    draw.text((24, 50), f"SYNTHETIC / MOCK · {len(decoded)} CUTS · HUMAN REVIEW REQUIRED", font=_font(12), fill=CORAL)
    for index, image in enumerate(decoded):
        column, row = index % columns, index // columns
        x, y = gap + column * (cell_width + gap), header + gap + row * (cell_height + gap)
        image.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
        draw.rounded_rectangle((x, y, x + cell_width, y + cell_height), radius=12,
                               fill="#F0F2EA", outline="#D7DED3", width=1)
        canvas.paste(image, (x + (cell_width - image.width) // 2,
                             y + (cell_height - image.height) // 2))
    return _png(canvas, cut_count=str(len(decoded)), unit_ids="\n".join(unit_ids))
