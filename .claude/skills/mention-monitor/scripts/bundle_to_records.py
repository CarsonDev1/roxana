"""Turn a capture bundle (browser/capture_batch.py) into store records.

Mechanical fields (link, author, exact times from tooltips, full text, metrics, evidence, comment tree, scroll_refs)
come from the bundle; only the judgement fields come from a classification file written after reading the post:

  {"source": {"tone", "claim_type", "importance", "importance_reason", "topics", "entities_mentioned",
              "transcriptions"?: {"1": "<chữ chép lại từ attach_01.png>"}, "notes"?},
   "comments": {"<fb_comment_id>": {"tone", "claim_type", "importance", "importance_reason"?, "topics",
                                    "entities_mentioned", "notes"?}}}

Usage:
  python bundle_to_records.py draft <bundle_dir> [--container-name N]          → prints what to classify
  python bundle_to_records.py apply <bundle_dir> <classification.json> --run RUN [--container-id FB-G0001]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from add_record import add_records
from common import TZ, Project, match_keywords, parse_iso, setup_stdout

VI_TIP = re.compile(r"(\d{1,2})\s+Tháng\s+(\d{1,2}),\s*(\d{4})\s+lúc\s+(\d{1,2}):(\d{2})", re.I)
EN_MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"], 1)}
EN_TIP = re.compile(r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s+at\s+(\d{1,2}):(\d{2})\s*([AP]M)", re.I)
REL = re.compile(r"^(\d+)\s*(giây|phút|giờ|ngày|tuần|tháng|năm)")
REL_UNIT = {"giây": timedelta(seconds=1), "phút": timedelta(minutes=1), "giờ": timedelta(hours=1),
            "ngày": timedelta(days=1), "tuần": timedelta(weeks=1), "tháng": timedelta(days=30), "năm": timedelta(days=365)}
REQUIRED_CLS = ("tone", "claim_type", "importance")


def parse_tooltip(tip: str | None) -> str | None:
    """'Thứ Hai, 7 Tháng 9, 2026 lúc 13:14' (or the English form) → ISO +07:00."""
    if not tip:
        return None
    m = VI_TIP.search(tip)
    if m:
        d, mo, y, h, mi = map(int, m.groups())
    else:
        m = EN_TIP.search(tip)
        if not m or m.group(1).lower() not in EN_MONTHS:
            return None
        mo, d, y, h, mi = EN_MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        h = h % 12 + (12 if m.group(6).upper() == "PM" else 0)
    return datetime(y, mo, d, h, mi, tzinfo=TZ).isoformat(timespec="seconds")


def relative(raw: str | None, base: str) -> str | None:
    m = REL.match((raw or "").strip())
    b = parse_iso(base)
    if not m or not b:
        return None
    return (b - int(m.group(1)) * REL_UNIT[m.group(2)]).isoformat(timespec="seconds")


def _num(s: str) -> int | None:
    m = re.match(r"^\s*([\d.,]+)\s*(K|N|nghìn|triệu|M)?\s*$", s or "", re.I)
    if not m:
        return None
    unit = (m.group(2) or "").lower()
    if unit:
        v = float(m.group(1).replace(".", "").replace(",", "."))  # "2,5K" = 2500
        return round(v * (1_000_000 if unit in ("m", "triệu") else 1_000))
    return int(m.group(1).replace(".", "").replace(",", ""))


def counts(raw: list[str], n_comments: int) -> dict:
    """Số liệu hiển thị dưới bài: [thích, bình luận, chia sẻ]; thiếu số nào thì Facebook không hiện số đó."""
    v = [x for x in (_num(r) for r in raw or []) if x is not None][:3]
    out = {"reactions": None, "comments": None, "shares": None}
    if not v:
        return out
    out["reactions"] = v[0]
    if len(v) == 3:
        out["comments"], out["shares"] = v[1], v[2]
    elif len(v) == 2:  # 2 số: bình luận nếu gần với số bình luận thu được, không thì là chia sẻ
        if n_comments and abs(v[1] - n_comments) <= max(2, 0.3 * v[1]):
            out["comments"] = v[1]
        else:
            out["shares"] = v[1]
    return out


def author_kind(name: str | None, href: str | None) -> str:
    if name and re.search(r"ẩn danh|anonymous", name, re.I):
        return "anonymous"
    if href and "/user/" in href or href and "profile.php" in href:
        return "person"
    return "page" if href else "unknown"


def _load(bundle: Path, name: str, default):
    f = bundle / name
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else default


def _at(log: dict, hhmmss: str) -> str:
    return f"{log['started_at'][:10]}T{hhmmss}+07:00"


def drafts(bundle: Path, container_id: str | None = None, container_name: str | None = None) -> dict:
    bundle = Path(bundle)
    feed, log = _load(bundle, "feed.json", {}), _load(bundle, "log.json", {})
    post = log.get("post") or {}
    steps = log.get("steps") or []
    posts = [s for s in steps if s["kind"] == "post"]
    scrolls = [s for s in steps if s["kind"] == "cscroll"]
    attach = [a for a in log.get("attachments") or [] if a.get("file")]
    captured = log.get("started_at")
    text = post.get("text") or feed.get("message") or ""
    posted = parse_tooltip(feed.get("tooltip") or post.get("tooltip"))
    raw_comments = _load(bundle, "p_comments.json", [])
    if post.get("counts_raw") is not None:
        metrics = {**counts(post["counts_raw"], len(raw_comments)), "views": None}
    else:
        metrics = {k: (post.get("metrics") or {}).get(k) for k in ("reactions", "comments", "shares", "views")}
    shared = post.get("shared")
    metrics["counted_at"] = _at(log, posts[-1]["at"]) if posts else captured
    attachments = [{"kind": "image", "description": a.get("alt") or "Ảnh đính kèm (văn bản)", "transcribed_text": None,
                    "url": a.get("url")} for a in attach]
    attachments += [{"kind": "image", "description": alt, "transcribed_text": None, "url": None}
                    for alt in (feed.get("image_alts") or []) if alt and not any(alt == a.get("alt") for a in attach)]
    media = [m for m in feed.get("media") or [] if "/photo" not in m]
    attachments += [{"kind": "video", "description": "Video/reel đính kèm", "transcribed_text": None, "url": m} for m in media]
    source = {
        "record_type": "source", "platform": "facebook",
        "content_type": "shared_post" if shared else "reel" if any("/reel/" in m for m in media) else "video" if media else "post",
        "shared_from": {"author_name": shared.get("author"), "author_url": shared.get("author_href"),
                        "text_excerpt": (shared.get("text") or "")[:500], "url": None} if shared else None,
        "url": feed["permalink"], "url_kind": "permalink", "container_id": container_id, "container_name": container_name,
        "author_name": post.get("author") or feed.get("author") or "(không rõ)",
        "author_url": post.get("author_href"), "author_kind": author_kind(post.get("author") or feed.get("author"), post.get("author_href")),
        "author_badge": post.get("badge"),
        "posted_at_raw": post.get("time_text") or feed.get("tooltip") or "", "posted_at": posted,
        "posted_at_precision": "exact" if posted else "unknown", "text": text, "attachments": attachments,
        "metrics": metrics, "captured_at": captured,
        "evidence": [{"file": s["shot"], "kind": "post", "shows": s["shows"], "captured_at": _at(log, s["at"]),
                      "capture_tool": "playwright"} for s in posts]
                    + [{"file": a["file"], "kind": "attach", "shows": f"Ảnh đính kèm phóng lớn (2x): {a.get('alt') or ''}".strip(),
                        "capture_tool": "playwright"} for a in attach]
                    + [{"file": s["shot"], "kind": "cscroll", "shows": s["shows"], "captured_at": _at(log, s["at"]),
                        "capture_tool": "playwright"} for s in scrolls],
        "snapshot_file": str(bundle / "p_snapshot.txt"),
        "notes": None if log.get("filter", "").startswith("Tất cả") else f"Bộ lọc bình luận: {log.get('filter')}",
    }
    times = {t.get("fb_comment_id"): t.get("tooltip") for t in _load(bundle, "times.json", [])}
    index = {c.get("fb_comment_id"): i for i, c in enumerate(raw_comments)}
    comments = []
    for c in raw_comments:
        fid = c.get("fb_comment_id")
        exact = parse_tooltip(times.get(fid))
        refs = [{"cscroll": n, "position": s["comments"].index(fid) + 1}
                for n, s in enumerate(scrolls, 1) if fid and fid in (s.get("comments") or [])]
        own = bundle / f"comment_{fid}.png"
        parent = c.get("parent_fb_comment_id")
        text_c = c.get("text") or "".join(c.get("emoji") or [])
        rec = {
            "record_type": "comment", "depth": 2 if parent else 1, "fb_comment_id": fid,
            "parent_comment_id": f"@{index[parent]}" if parent in index else None,
            "url": re.sub(r"[?&]__cft__.*$", "", c.get("comment_url") or "") or None,
            "author_name": c.get("author") or "(không rõ)", "author_url": c.get("author_href"),
            "author_kind": author_kind(c.get("author"), c.get("author_href")),
            "posted_at_raw": c.get("time_text") or "", "posted_at": exact or relative(c.get("time_text"), captured),
            "posted_at_precision": "exact" if exact else "relative_estimate" if c.get("time_text") else "unknown",
            "text": text_c,
            "attachments": [{"kind": "image", "description": f"Nhãn dán: {s}", "transcribed_text": None, "url": None}
                            for s in c.get("stickers") or []],
            "reactions": next((int(m.group(1)) for r in c.get("reacts") or [] if (m := re.match(r"(\d+)\s*cảm xúc", r))), 0),
            "scroll_refs": refs, "captured_at": captured,
            "evidence": [{"file": str(own), "kind": "comment", "shows": "Ảnh riêng bình luận (2x)",
                          "capture_tool": "playwright"}] if own.exists() else None,
        }
        comments.append(rec)
    classify = {
        "source": {"author": source["author_name"], "posted_at": posted, "text": text, "shared_from": source["shared_from"],
                   "attachments": [a["description"] for a in attachments],
                   "attach_files": [a["file"] for a in attach], "container": container_name},
        "comments": [{"fb_comment_id": c["fb_comment_id"], "depth": c["depth"], "author": c["author_name"],
                      "text": c["text"], "reactions": c["reactions"],
                      "stickers": [a["description"] for a in c["attachments"]]} for c in comments],
    }
    return {"source": source, "comments": comments, "classify": classify}


def _merge(rec: dict, cls: dict, what: str) -> None:
    missing = [k for k in REQUIRED_CLS if not cls.get(k)]
    if missing:
        raise ValueError(f"{what}: thiếu phân loại {', '.join(missing)}")
    for k in ("tone", "claim_type", "importance", "importance_reason", "topics", "entities_mentioned"):
        if k in cls:
            rec[k] = cls[k]
    rec.setdefault("topics", []), rec.setdefault("entities_mentioned", [])
    if cls.get("notes"):
        rec["notes"] = "; ".join(filter(None, [rec.get("notes"), cls["notes"]]))


def apply_bundle(project: Project, bundle: Path, cls: dict, run_id: str, container_id: str | None,
                 container_name: str | None) -> dict:
    config = project.load_config()
    d = drafts(Path(bundle), container_id, container_name)
    src = d["source"]
    _merge(src, cls.get("source") or {}, "bài")
    for i, t in (cls["source"].get("transcriptions") or {}).items():
        idx = int(i) - 1
        if 0 <= idx < len(src["attachments"]):
            src["attachments"][idx]["transcribed_text"] = t
    for c in d["comments"]:
        _merge(c, (cls.get("comments") or {}).get(c["fb_comment_id"]) or {}, f"bình luận {c['fb_comment_id']}")
    body = " ".join([src["text"]] + [a.get("transcribed_text") or "" for a in src["attachments"]])
    src["keywords_matched"], _ = match_keywords(body, config, container_name or "")
    [res] = add_records(project, [src], run_id, config)
    out = {"source": res, "comments": []}
    if res["status"] != "added":
        return out
    scroll_paths = [p for p in res["evidence_paths"] if "_cscroll_" in p]
    batch = []
    for c in d["comments"]:
        c["source_id"] = res["id"]
        c["scroll_refs"] = [{"file": scroll_paths[r["cscroll"] - 1], "position": r["position"]}
                            for r in c["scroll_refs"] if r["cscroll"] <= len(scroll_paths)]
        c["keywords_matched"], _ = match_keywords(c["text"], config, f"{container_name or ''} {src['text']}")
        if c.get("evidence") is None:
            c.pop("evidence")
        batch.append(c)
    out["comments"] = add_records(project, batch, run_id, config) if batch else []
    return out


def _iso_any(value: str | None) -> tuple[str | None, bool]:
    """ISO / 'M/D/YYYY h:mm:ss AM' → (ISO +07:00, has_time)."""
    if not value:
        return None, False
    v = value.strip()
    try:
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        has_time = "T" in v or ":" in v
    except ValueError:
        m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})(?::\d{2})?\s*([AP]M)?", v, re.I)
        if not m:
            return None, False
        mo, d, y, h, mi = (int(x) for x in m.groups()[:5])
        if m.group(6):
            h = h % 12 + (12 if m.group(6).upper() == "PM" else 0)
        dt, has_time = datetime(y, mo, d, h, mi, tzinfo=TZ), True
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ).isoformat(timespec="seconds"), has_time


def article_draft(bundle: Path) -> dict:
    """Web article bundle (webscan/capture_articles.py) → source record without classification."""
    bundle = Path(bundle)
    meta = _load(bundle, "meta.json", {})
    cand = meta.get("candidate") or {}
    posted, exact = _iso_any(meta.get("published"))
    precision = "exact" if posted and exact else "day" if posted else "unknown"
    if not posted and cand.get("published"):
        posted, precision = _iso_any(cand["published"])[0], "day"  # ngày theo nguồn tin (Google News), không có giờ chắc chắn
    site = cand.get("source_name") or meta.get("site")
    date = (meta.get("captured_at") or "")[:10]
    return {
        "record_type": "source", "platform": "web", "content_type": "article",
        "url": meta.get("canonical") or meta.get("final"), "url_kind": "permalink",
        "container_name": site, "author_name": meta.get("author") or site, "author_url": None, "author_kind": "page",
        "posted_at_raw": meta.get("published") or cand.get("published") or "", "posted_at": posted,
        "posted_at_precision": precision, "text": (bundle / "article.txt").read_text(encoding="utf-8"),
        "attachments": [], "metrics": {}, "captured_at": meta.get("captured_at"),
        "evidence": [{"file": s["file"], "kind": "post",
                      "shows": f"Bài báo — tiêu đề và nội dung (phần {i}/{len(meta.get('shots') or [])})",
                      "captured_at": f"{date}T{s['at']}+07:00" if date and s.get("at") else None,
                      "capture_tool": "playwright"} for i, s in enumerate(meta.get("shots") or [], 1)],
        "snapshot_file": str(bundle / "article.txt"),
        "notes": f"Tiêu đề: {meta.get('title')}. Bản HTML gốc lưu kèm: {bundle / 'article.html'}",
    }


def apply_article(project: Project, bundle: Path, cls: dict, run_id: str) -> dict:
    config = project.load_config()
    src = article_draft(Path(bundle))
    _merge(src, cls.get("source") or {}, "bài báo")
    src["keywords_matched"], _ = match_keywords(src["text"], config)
    [res] = add_records(project, [src], run_id, config)
    return res


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--project")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("draft")
    a.add_argument("bundle")
    a.add_argument("--container-name")
    b = sub.add_parser("apply")
    b.add_argument("bundle")
    b.add_argument("cls")
    b.add_argument("--run", required=True)
    b.add_argument("--container-id")
    b.add_argument("--container-name")
    args = ap.parse_args(argv)
    project = Project(args.project) if args.project else Project()
    if args.cmd == "draft":
        print(json.dumps(drafts(Path(args.bundle), None, args.container_name)["classify"], ensure_ascii=False, indent=1))
    else:
        cls = json.loads(Path(args.cls).read_text(encoding="utf-8"))
        print(json.dumps(apply_bundle(project, Path(args.bundle), cls, args.run, args.container_id, args.container_name),
                         ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
