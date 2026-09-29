"""Shared helpers for the mention-monitor scripts: project paths, time, JSONL store, ids, normalisation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TZ = timezone(timedelta(hours=7))
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECT = SCRIPTS_DIR.parents[3]  # scripts -> mention-monitor -> skills -> .claude -> project

PLATFORM_CODES = {"facebook": "FB", "web": "WEB", "youtube": "YT", "tiktok": "TT"}
PLATFORM_ID_TYPES = {"source": ("P", 5), "comment": ("C", 6), "container": ("G", 4)}
GLOBAL_ID_TYPES = {"search_log": ("LOG-", 6), "recheck": ("CHK-", 6), "exclusion": ("EXC-", 6), "event": ("EVT-", 4)}

FB_HOSTS = {"facebook.com", "www.facebook.com", "m.facebook.com", "mbasic.facebook.com",
            "web.facebook.com", "touch.facebook.com", "mobile.facebook.com"}
FB_KEEP_PARAMS = {"fbid", "set", "v", "story_fbid", "id", "comment_id", "reply_comment_id"}
DROP_PARAMS = {"fbclid", "gclid", "mibextid"}
_ID_RE = re.compile(r"^(.*?)(\d+)$")


def setup_stdout() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ)


class Project:
    def __init__(self, root: Path | str = DEFAULT_PROJECT):
        self.root = Path(root).resolve()

    @property
    def records_path(self) -> Path:
        return self.root / "data" / "records.jsonl"

    @property
    def config_path(self) -> Path:
        return self.root / "config.json"

    def load_config(self) -> dict:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def save_config(self, config: dict) -> None:
        tmp = self.config_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.config_path)

    def screenshots_dir(self, platform: str, day: str) -> Path:
        return self.root / "screenshots" / platform / day

    def snapshots_dir(self, platform: str, day: str) -> Path:
        return self.root / "snapshots" / platform / day

    def run_dir(self, run_id: str) -> Path:
        return self.root / "runs" / run_id

    def output_path(self, config: dict) -> Path:
        return self.root / "output" / config.get("output_file", "Tong_hop.xlsx")

    @property
    def thumbs_dir(self) -> Path:
        return self.root / "output" / "thumbs"

    def resolve(self, path: str | Path) -> Path:
        p = Path(path)
        return p if p.is_absolute() else self.root / p

    def rel(self, path: str | Path) -> str:
        return Path(path).resolve().relative_to(self.root).as_posix()


def read_records(path: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    warnings: list[str] = []
    if not path.exists():
        return records, warnings
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                warnings.append(f"records.jsonl dòng {lineno} không phải JSON hợp lệ — đã bỏ qua")
    return records, warnings


def _ends_with_newline(path: Path) -> bool:
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        return f.read(1) == b"\n"


def append_records(path: Path, records: list[dict]) -> None:
    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_newline = path.exists() and path.stat().st_size > 0 and not _ends_with_newline(path)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        if needs_newline:
            f.write("\n")
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def id_prefix(record_type: str, platform: str | None) -> tuple[str, int]:
    if record_type in PLATFORM_ID_TYPES:
        letter, width = PLATFORM_ID_TYPES[record_type]
        return f"{PLATFORM_CODES[platform]}-{letter}", width
    return GLOBAL_ID_TYPES[record_type]


class IdAllocator:
    def __init__(self, records: list[dict]):
        self._max: dict[str, int] = {}
        for rec in records:
            self.observe(rec.get("id", ""))

    def observe(self, record_id: str) -> None:
        match = _ID_RE.match(record_id or "")
        if match:
            prefix, number = match.group(1), int(match.group(2))
            self._max[prefix] = max(self._max.get(prefix, 0), number)

    def next(self, record_type: str, platform: str | None = None) -> str:
        prefix, width = id_prefix(record_type, platform)
        number = self._max.get(prefix, 0) + 1
        self._max[prefix] = number
        return f"{prefix}{number:0{width}d}"


def nfc(text: str | None) -> str:
    return unicodedata.normalize("NFC", text or "")


def norm_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", nfc(text)).strip()


def strip_accents(text: str | None) -> str:
    text = nfc(text).replace("đ", "d").replace("Đ", "D")
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def fold(text: str | None) -> str:
    """Accent-, case- and whitespace-insensitive form used for matching."""
    return strip_accents(norm_text(text)).lower()


def short_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_url(url: str | None) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    parts = urlsplit(url)
    host = parts.netloc.lower()
    params = parse_qsl(parts.query, keep_blank_values=True)
    if host in FB_HOSTS:
        host = "www.facebook.com"
        params = [(k, v) for k, v in params if k in FB_KEEP_PARAMS]
    else:
        params = [(k, v) for k, v in params if k not in DROP_PARAMS and not k.startswith("utm_")]
    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit(("https", host, path, urlencode(sorted(params)), ""))


def match_keywords(text: str, config: dict, context_text: str = "") -> tuple[list[str], list[str]]:
    """Return (matched group ids, group ids found but dropped for lack of a context term)."""
    folded = fold(text)
    context = fold(f"{text} {context_text}")
    has_context = any(fold(term) in context for term in config.get("context_terms", []))
    matched: list[str] = []
    lacking: list[str] = []
    for group in config.get("keyword_groups", []):
        if not any(fold(term) in folded for term in group["terms"]):
            continue
        if group.get("requires_context") and not has_context:
            lacking.append(group["id"])
        else:
            matched.append(group["id"])
    return matched, lacking


def dedupe_key(rec: dict) -> str | None:
    kind = rec.get("record_type")
    if kind == "source":
        if rec.get("url_kind") == "permalink" and rec.get("url"):
            return "url:" + normalize_url(rec["url"])
        return "src:" + short_hash(rec.get("container_id") or "", norm_text(rec.get("author_name")),
                                   norm_text(rec.get("text"))[:200])
    if kind == "comment":
        if rec.get("fb_comment_id"):
            return f"fbc:{rec['fb_comment_id']}"
        return "cmt:" + short_hash(rec.get("source_id") or "", norm_text(rec.get("author_name")),
                                   norm_text(rec.get("text")))
    if kind == "container":
        return "ctr:" + normalize_url(rec.get("url"))
    if kind == "event":
        return "evt:" + short_hash(norm_text(rec.get("date_raw")), norm_text(rec.get("description"))[:200])
    return None
