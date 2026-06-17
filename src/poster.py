from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

# ── Font loading ──────────────────────────────────────────────────────────

_FONT_CACHE: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _get_chinese_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try system Chinese fonts, fall back to Pillow default."""
    if size in _FONT_CACHE:
        return _FONT_CACHE[size]

    font: Optional[ImageFont.FreeTypeFont] = None

    candidates = [
        "WenQuanYi Zen Hei",
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "SimHei",
        "Microsoft YaHei",
    ]

    for name in candidates:
        try:
            font = ImageFont.truetype(name, size)
            if font:
                break
        except OSError:
            pass

    if font is None:
        path_candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        ]
        for path in path_candidates:
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size)
                    break
                except OSError:
                    pass

    if font is None:
        font = ImageFont.load_default()

    _FONT_CACHE[size] = font
    return font


# ── Team visual config ────────────────────────────────────────────────────

# (primary_hex, text_on_primary, accent_hex)
TEAM_COLORS: dict[str, tuple[str, str, str]] = {
    "阿根廷": ("#5B9BD5", "#FFFFFF", "#3A7BC8"),
    "法国": ("#1A237E", "#FFFFFF", "#0D1452"),
    "巴西": ("#009C3B", "#FFFFFF", "#007A2E"),
    "摩洛哥": ("#C1272D", "#FFFFFF", "#A01E24"),
    "日本": ("#1A237E", "#FFFFFF", "#BC002D"),
    "克罗地亚": ("#C8102E", "#FFFFFF", "#A00D24"),
}

_FALLBACK_COLOR = ("#333333", "#FFFFFF", "#555555")

TEAM_FLAGS: dict[str, str] = {
    "阿根廷": "🇦🇷",
    "法国": "🇫🇷",
    "巴西": "🇧🇷",
    "摩洛哥": "🇲🇦",
    "日本": "🇯🇵",
    "克罗地亚": "🇭🇷",
}


# ── Text helpers ──────────────────────────────────────────────────────────

def _wrap_text(text: str, max_chars_per_line: int) -> list[str]:
    """Simple character-count wrap for Chinese text."""
    lines: list[str] = []
    current = ""
    for char in text:
        if char == "\n":
            if current:
                lines.append(current)
            lines.append("")
            current = ""
            continue
        current += char
        if len(current) >= max_chars_per_line:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return [ln for ln in lines if ln or (ln == "" and lines and lines[-1] == "")]


def _draw_multiline_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: list[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    anchor: str = "la",
    line_spacing: int = 6,
) -> int:
    """Draw multi-line text.  Returns bottom y after drawing."""
    x, y = xy
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font, anchor=anchor)
        y += font.size + line_spacing
    return y


# ── Poster generator ──────────────────────────────────────────────────────

def generate_poster(
    team_name: str,
    persona: str,
    reason: str,
    copy_text: str,
    *,
    width: int = 600,
    height: int = 800,
) -> Image.Image:
    """Generate a shareable World Cup team personality card."""

    primary, text_on_primary, accent = TEAM_COLORS.get(
        team_name, _FALLBACK_COLOR
    )
    flag = TEAM_FLAGS.get(team_name, "")

    # Canvas
    img = Image.new("RGB", (width, height), "#FFF9F5")
    draw = ImageDraw.Draw(img)

    # ── Top banner ──────────────────────────────────────────────────────
    banner_h = 72
    draw.rectangle([(0, 0), (width, banner_h)], fill=primary)

    banner_font = _get_chinese_font(22)
    banner_title = "⚽  2026世界杯 · 我的主队人格卡"
    # Try team flag in banner
    if flag:
        banner_title = f"{flag}  {banner_title}"
    draw.text(
        (width // 2, banner_h // 2),
        banner_title,
        fill=text_on_primary,
        font=banner_font,
        anchor="mm",
    )

    # ── Decorative line under banner ────────────────────────────────────
    draw.rectangle([(0, banner_h), (width, banner_h + 4)], fill=accent)

    # ── Flag & Team name section ────────────────────────────────────────
    cur_y = banner_h + 50

    # Flag emoji — rendered as its own block.  Most CJK fonts won't draw
    # flag glyphs, so we fall back to a decorative star.
    flag_glyph = flag if flag else "★"
    flag_font = _get_chinese_font(56)
    draw.text(
        (width // 2, cur_y),
        flag_glyph,
        fill=primary,
        font=flag_font,
        anchor="mt",
    )
    cur_y += flag_font.size + 16

    # Team name
    team_font = _get_chinese_font(42)
    draw.text(
        (width // 2, cur_y),
        team_name,
        fill=primary,
        font=team_font,
        anchor="mt",
    )
    cur_y += team_font.size + 20

    # ── Persona badge ───────────────────────────────────────────────────
    badge_text = f"🎭  {persona}"
    badge_font = _get_chinese_font(20)
    badge_pad_x, badge_pad_y = 28, 12

    # Measure badge text
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = bbox[2] - bbox[0] + badge_pad_x * 2
    badge_h = bbox[3] - bbox[1] + badge_pad_y * 2
    badge_left = (width - badge_w) // 2
    badge_top = cur_y
    badge_radius = 20

    draw.rounded_rectangle(
        [(badge_left, badge_top), (badge_left + badge_w, badge_top + badge_h)],
        radius=badge_radius,
        fill=primary,
    )
    draw.text(
        (width // 2, badge_top + badge_h // 2),
        badge_text,
        fill=text_on_primary,
        font=badge_font,
        anchor="mm",
    )
    cur_y = badge_top + badge_h + 36

    # ── Reason card ─────────────────────────────────────────────────────
    reason_prefix = "推荐理由"
    reason_body = reason.replace("推荐理由：", "").replace("推荐理由:", "").strip()
    reason_font = _get_chinese_font(17)
    reason_title_font = _get_chinese_font(18)
    reason_lines = _wrap_text(reason_body, 22)
    card_pad_x, card_pad_y = 32, 24
    card_width = width - 80

    # Measure
    max_line_w = 0
    for ln in reason_lines:
        b = draw.textbbox((0, 0), ln, font=reason_font)
        max_line_w = max(max_line_w, b[2] - b[0])
    card_content_h = (
        24  # title line
        + 8  # gap
        + len(reason_lines) * (reason_font.size + 6)
    )
    card_h = card_content_h + card_pad_y * 2
    card_left = (width - card_width) // 2

    # Card background
    draw.rounded_rectangle(
        [(card_left, cur_y), (card_left + card_width, cur_y + card_h)],
        radius=14,
        fill="#FFFFFF",
        outline=primary,
        width=1,
    )

    # Title
    draw.text(
        (card_left + card_pad_x, cur_y + card_pad_y),
        f"💡 {reason_prefix}",
        fill=primary,
        font=reason_title_font,
        anchor="lt",
    )
    # Body
    body_y = cur_y + card_pad_y + 30
    _draw_multiline_text(
        draw,
        (card_left + card_pad_x, body_y),
        reason_lines,
        font=reason_font,
        fill="#444444",
        anchor="la",
        line_spacing=5,
    )
    cur_y = cur_y + card_h + 36

    # ── Social copy section ─────────────────────────────────────────────
    copy_font = _get_chinese_font(18)
    copy_lines = _wrap_text(copy_text, 24)
    copy_y = cur_y

    # Left quote decoration
    quote_font = _get_chinese_font(36)
    draw.text(
        (40, copy_y - 8),
        '"',
        fill=primary,
        font=quote_font,
        anchor="lt",
    )

    copy_text_y = _draw_multiline_text(
        draw,
        (66, copy_y),
        copy_lines,
        font=copy_font,
        fill="#555555",
        anchor="la",
        line_spacing=6,
    )

    # Right quote decoration
    last_line_bbox = draw.textbbox((0, 0), copy_lines[-1] if copy_lines else "", font=copy_font)
    draw.text(
        (66 + last_line_bbox[2] + 4, copy_text_y - copy_font.size - 2),
        '"',
        fill=primary,
        font=quote_font,
        anchor="lt",
    )
    cur_y = copy_text_y + 40

    # ── Footer ──────────────────────────────────────────────────────────
    footer_font = _get_chinese_font(14)
    footer_url_font = _get_chinese_font(15)
    draw.line(
        [(60, cur_y), (width - 60, cur_y)],
        fill=primary,
        width=1,
    )
    cur_y += 18

    draw.text(
        (width // 2, cur_y),
        "扫码测测你的世界杯主队人格",
        fill="#888888",
        font=footer_font,
        anchor="mt",
    )
    cur_y += footer_font.size + 8
    draw.text(
        (width // 2, cur_y),
        "world-cup-agent.streamlit.app",
        fill=primary,
        font=footer_url_font,
        anchor="mt",
    )

    # ── Bottom decorative stripe ────────────────────────────────────────
    cur_y += footer_url_font.size + 20
    draw.rectangle([(0, height - 6), (width, height)], fill=primary)

    return img


def poster_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL image to PNG bytes."""
    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    return buf.getvalue()
