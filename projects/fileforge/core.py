"""Dependency-free logic for fileforge.

All logic that can be exercised without Qt lives here: extension tables,
conversion dispatch, text transformations and ffmpeg argument builders.
"""

import csv
import html
from html.parser import HTMLParser
import io
import json
import os
import re
import subprocess

VERSION = "0.1.0"

TEXT_EXTS = {".txt", ".md", ".html", ".json", ".csv"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUDIO_EXTS = {".wav", ".mp3", ".ogg", ".m4a"}


class ConversionError(ValueError):
    """A user-facing conversion error (never a traceback)."""


def _ext(path):
    return os.path.splitext(str(path))[1].lower()


def _norm_ext(ext):
    ext = str(ext).lower()
    return ext if ext.startswith(".") else "." + ext


# ---------------------------------------------------------------------------
# Text conversions
# ---------------------------------------------------------------------------

def _txt_to_md(text):
    """Wrap plain-text paragraphs into Markdown paragraphs."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return "\n\n".join(paragraphs) + ("\n" if paragraphs else "")


def _inline_html(value):
    escaped = html.escape(value)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__(.+?)__", r"<strong>\1</strong>", escaped)
    return escaped


def _md_to_html(text):
    """Render a small Markdown subset as escaped HTML (headings/bold/lists)."""
    out = []
    list_type = None

    def close_list():
        nonlocal list_type
        if list_type:
            out.append("</%s>" % list_type)
            list_type = None

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_list()
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (level, _inline_html(heading.group(2)), level))
            continue
        bullet = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if bullet:
            if list_type != "ul":
                close_list()
                out.append("<ul>")
                list_type = "ul"
            out.append("<li>%s</li>" % _inline_html(bullet.group(1)))
            continue
        numbered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if numbered:
            if list_type != "ol":
                close_list()
                out.append("<ol>")
                list_type = "ol"
            out.append("<li>%s</li>" % _inline_html(numbered.group(1)))
            continue
        if not line.strip():
            close_list()
            continue
        close_list()
        out.append("<p>%s</p>" % _inline_html(line))
    close_list()
    return "\n".join(out) + ("\n" if out else "")


class _TextExtractor(HTMLParser):
    _BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "h1", "h2", "h3",
              "h4", "h5", "h6", "section", "article"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._BLOCK:
            self.parts.append("\n")


def _html_to_txt(text):
    """Strip HTML tags using html.parser and return readable plain text."""
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    lines = [line.strip() for line in "".join(parser.parts).splitlines()]
    kept = [line for line in lines if line]
    return "\n".join(kept) + ("\n" if kept else "")


def _txt_to_json(text):
    return json.dumps({"text": text}, indent=2) + "\n"


def _json_to_txt(text):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ConversionError("invalid JSON: %s" % exc) from exc
    if isinstance(data, dict) and isinstance(data.get("text"), str):
        return data["text"]
    return json.dumps(data, indent=2) + "\n"


def _txt_to_csv(text):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for line in text.splitlines():
        writer.writerow([line])
    return buffer.getvalue()


def _csv_to_txt(text):
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise ConversionError("invalid CSV: %s" % exc) from exc
    lines = [",".join(row) for row in rows if row]
    return "\n".join(lines) + ("\n" if lines else "")


def _csv_to_json(text):
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except csv.Error as exc:
        raise ConversionError("invalid CSV: %s" % exc) from exc
    return json.dumps(rows, indent=2) + "\n"


def _json_to_csv(text):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ConversionError("invalid JSON: %s" % exc) from exc
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise ConversionError("JSON must be a list of objects for CSV conversion")
    if not data:
        return ""
    fields = list(dict.fromkeys(key for row in data for key in row))
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    return buffer.getvalue()


_TEXT_CONVERTERS = {
    (".txt", ".md"): _txt_to_md,
    (".md", ".html"): _md_to_html,
    (".html", ".txt"): _html_to_txt,
    (".txt", ".json"): _txt_to_json,
    (".json", ".txt"): _json_to_txt,
    (".txt", ".csv"): _txt_to_csv,
    (".csv", ".txt"): _csv_to_txt,
    (".csv", ".json"): _csv_to_json,
    (".json", ".csv"): _json_to_csv,
}


def supported_targets(path):
    """Return sorted output extensions that are valid for *path*."""
    src = _ext(path)
    if src in TEXT_EXTS:
        return sorted(dst for (origin, dst) in _TEXT_CONVERTERS if origin == src)
    if src in IMAGE_EXTS:
        return sorted(IMAGE_EXTS - {src})
    if src in AUDIO_EXTS:
        return sorted(AUDIO_EXTS - {src})
    return []


def convert_text(text, src_ext, dst_ext):
    """Convert *text* between the supported text formats."""
    src, dst = _norm_ext(src_ext), _norm_ext(dst_ext)
    if src not in TEXT_EXTS:
        raise ConversionError("unsupported source text extension: %s" % src)
    if dst not in TEXT_EXTS:
        raise ConversionError("unsupported target text extension: %s" % dst)
    converter = _TEXT_CONVERTERS.get((src, dst))
    if converter is None:
        raise ConversionError("cannot convert %s to %s" % (src, dst))
    return converter(text)


# ---------------------------------------------------------------------------
# Media conversions
# ---------------------------------------------------------------------------

_IMAGE_FILTER = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
_AUDIO_CODECS = {".mp3": "libmp3lame", ".ogg": "libvorbis",
                 ".m4a": "aac", ".wav": "pcm_s16le"}


def build_media_command(src, dst):
    """Build an ffmpeg argv list for an image or audio conversion."""
    source, target = _ext(src), _ext(dst)
    if source in IMAGE_EXTS and target in IMAGE_EXTS and source != target:
        return ["ffmpeg", "-y", "-i", str(src), "-vf", _IMAGE_FILTER, str(dst)]
    if source in AUDIO_EXTS and target in AUDIO_EXTS and source != target:
        command = ["ffmpeg", "-y", "-i", str(src),
                   "-codec:a", _AUDIO_CODECS[target]]
        if target in (".mp3", ".ogg", ".m4a"):
            command += ["-b:a", "192k"]
        command.append(str(dst))
        return command
    raise ConversionError("cannot convert %s to %s" % (source or "(none)",
                                                       target or "(none)"))


def convert_file(src, dst, runner=None):
    """Convert a file on disk, dispatching to text logic or ffmpeg."""
    source, target = _ext(src), _ext(dst)
    if target not in supported_targets(src):
        raise ConversionError("cannot convert %s to %s" % (source or "(none)",
                                                           target or "(none)"))
    if source in TEXT_EXTS:
        try:
            with open(src, encoding="utf-8") as handle:
                result = convert_text(handle.read(), source, target)
        except OSError as exc:
            raise ConversionError("cannot read %s: %s" % (src, exc)) from exc
        try:
            with open(dst, "w", encoding="utf-8") as handle:
                handle.write(result)
        except OSError as exc:
            raise ConversionError("cannot write %s: %s" % (dst, exc)) from exc
        return str(dst)

    command = build_media_command(src, dst)
    run = runner or subprocess.run
    try:
        run(command, check=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ConversionError("ffmpeg failed: %s" % exc) from exc
    return str(dst)
