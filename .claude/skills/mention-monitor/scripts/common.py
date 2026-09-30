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


def normalize_author_url(url: str) -> str:
    """Stable profile link: Facebook adds per-page-load tokens (__cft__, __tn__) and comment ids to name links."""
    parts = urlsplit(url.strip() if "://" in url else "https://" + url.strip())
    if parts.netloc.lower() not in FB_HOSTS:
        return url.strip()
    clean = urlsplit(normalize_url(url))
    params = [(k, v) for k, v in parse_qsl(clean.query) if k not in ("comment_id", "reply_comment_id")]
    return urlunsplit((clean.scheme, clean.netloc, clean.path, urlencode(params), ""))


class _Haystack:
    """Text prepared for term search: lower-cased, plus a per-character accent-free copy at the same positions."""

    def __init__(self, text: str):
        self.low = norm_text(text).lower()
        self.flat = "".join(f if len(f := strip_accents(ch).lower()) == 1 else ch for ch in self.low)

    def has(self, term: str) -> bool:
        """Whole-word, case-insensitive. Each character must be written either exactly as in the term or without
        its accent — "Tuong Phong"/"tường phong" match "Tường Phong", "tường phòng" does not."""
        t = norm_text(term).lower()
        ft = "".join(f if len(f := strip_accents(ch).lower()) == 1 else ch for ch in t)
        if not ft:
            return False
        i = self.flat.find(ft)
        while i >= 0:
            j = i + len(ft)
            bounded = (i == 0 or not self.flat[i - 1].isalnum() or not ft[0].isalnum()) and \
                      (j == len(self.flat) or not self.flat[j].isalnum() or not ft[-1].isalnum())
            if bounded and all(o == a or o == p for o, a, p in zip(self.low[i:j], t, ft)):
                return True
            i = self.flat.find(ft, i + 1)
        return False


def match_keywords(text: str, config: dict, context_text: str = "") -> tuple[list[str], list[str]]:
    """Return (matched group ids, group ids found but dropped for lack of a context term).

    A group matches on any of its `terms`. `weak_terms` (a bare name that is also a person's or place's name) count
    only with context: a context term that is not one of the group's own terms, or another group's match.
    `requires_context` groups need context for every term."""
    body, ctx = _Haystack(text), _Haystack(f"{text} {context_text}")
    ctx_found = [t for t in config.get("context_terms", []) if ctx.has(t)]
    groups = config.get("keyword_groups", [])
    strong = {g["id"] for g in groups if any(body.has(t) for t in g["terms"])}
    weak = {g["id"] for g in groups if g["id"] not in strong and any(body.has(t) for t in g.get("weak_terms", []))}
    matched: list[str] = []
    lacking: list[str] = []
    for g in groups:
        if g["id"] not in strong | weak:
            continue
        own = {fold(t) for t in g["terms"] + g.get("weak_terms", [])}
        outside = any(fold(t) not in own for t in ctx_found) or bool((strong | weak) - {g["id"]})
        if g["id"] in weak:
            ok = outside
        elif g.get("requires_context"):
            ok = bool(ctx_found) or bool(strong - {g["id"]})
        else:
            ok = True
        (matched if ok else lacking).append(g["id"])
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
        if rec.get("yt_comment_id"):
            return f"ytc:{rec['yt_comment_id']}"
        return "cmt:" + short_hash(rec.get("source_id") or "", norm_text(rec.get("author_name")),
                                   norm_text(rec.get("text")))
    if kind == "container":
        return "ctr:" + normalize_url(rec.get("url"))
    if kind == "event":
        return "evt:" + short_hash(norm_text(rec.get("date_raw")), norm_text(rec.get("description"))[:200])
    if kind == "search_log":  # cùng một lượt tìm (nền tảng, mục, từ khoá, bộ lọc, nhóm, giờ bắt đầu) chỉ ghi một lần
        return "log:" + short_hash(rec.get("platform") or "", rec.get("section") or "", norm_text(rec.get("query")),
                                   json.dumps(rec.get("filters") or {}, sort_keys=True), rec.get("container_id") or "",
                                   rec.get("started_at") or "")
    if kind == "exclusion":
        return "exc:" + normalize_url(rec.get("url"))
    return None
