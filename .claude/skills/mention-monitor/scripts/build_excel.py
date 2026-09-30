"""Build the evidence workbook (output/<output_file>) from data/records.jsonl.

Usage: python build_excel.py [--project D:\\Roxana]
Prints {"status": "ok", "file", "counts", "warnings"}, or {"status": "error", "error"} and exits 1
when the output file is open in Excel.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from openpyxl import Workbook

from common import Project, now_iso, parse_iso, read_records, setup_stdout
from schema import DESCRIPTIONS, LABELS, label
from view import View, build_view, needs_join
from xlsx_helpers import (BOLD, BORDER, SECTION_FILL, TITLE_FONT, YELLOW_FILL, Column, Formula, Img, Internal,
                          Link, col_letter, countif, countif_literal, setup_print, sheet_warnings, write_cell,
                          write_table)

S_OVERVIEW = "Tổng quan"
S_TIMELINE = "Dòng thời gian"
S_SOURCES = "Bài viết & Nguồn"
S_COMMENTS = "Bình luận"
S_PEOPLE = "Người & Tổ chức"
S_CONTAINERS = "Nhóm & Trang"
S_EVIDENCE = "Bằng chứng quan trọng"
S_LOG = "Nhật ký quét"
S_CHANGES = "Lịch sử thay đổi"
S_EXCLUDED = "Đã loại trừ"
S_LEGEND = "Chú thích"
SHEET_ORDER = [S_OVERVIEW, S_TIMELINE, S_SOURCES, S_COMMENTS, S_PEOPLE, S_CONTAINERS, S_EVIDENCE, S_LOG,
               S_CHANGES, S_EXCLUDED, S_LEGEND]
SHEET_DESCRIPTIONS = {
    S_TIMELINE: "Các mốc chính của vụ việc, kèm nguồn và độ tin cậy",
    S_SOURCES: "Mỗi dòng một bài viết / bài báo: nội dung nguyên văn, ảnh chụp, người đăng, phân loại",
    S_COMMENTS: "Mỗi dòng một bình luận hoặc trả lời, theo thứ tự cây bình luận của từng bài",
    S_PEOPLE: "Các bên liên quan và người đăng / bình luận, số bài và số lần được nhắc",
    S_CONTAINERS: "Nhóm và trang đã biết; dòng tô vàng là nhóm kín cần xin vào",
    S_EVIDENCE: "Bài và bình luận mức quan trọng Cao, ảnh lớn — dùng làm danh mục khi lập vi bằng",
    S_LOG: "Mọi lần tìm kiếm / cuộn feed, kèm giới hạn gặp phải",
    S_CHANGES: "Bài bị sửa, bị xoá, hoặc số tương tác tăng khi kiểm tra lại",
    S_EXCLUDED: "Kết quả trùng tên đã loại (không ghi tên người đăng)",
    S_LEGEND: "Ý nghĩa các cột, cách phân loại, cách kiểm tra mã SHA-256",
}
TAB_COLORS = {S_OVERVIEW: "548235", S_TIMELINE: "548235", S_EVIDENCE: "548235",
              S_SOURCES: "2F5597", S_COMMENTS: "2F5597", S_PEOPLE: "2F5597", S_CONTAINERS: "2F5597",
              S_LOG: "7F7F7F", S_CHANGES: "7F7F7F", S_EXCLUDED: "7F7F7F", S_LEGEND: "BF8F00"}
NO_IMAGE = "Chưa có ảnh"
MONTH_UNKNOWN = "Không rõ"
PLATFORMS = ["facebook", "web", "youtube", "tiktok"]
METRIC_NAMES = {"reactions": "Thích", "comments": "Bình luận", "shares": "Chia sẻ", "views": "Lượt xem",
                "reply_count": "Phản hồi"}
ATTACHMENT_KINDS = {"image": "Ảnh", "video": "Video", "link": "Link", "document": "Tài liệu"}


class ExcelLockedError(RuntimeError):
    """The output workbook is open in another program (usually Excel)."""


def fmt_time(value, precision=None) -> str:
    dt = parse_iso(value)
    if dt is None:
        return ""
    if precision == "year":
        return dt.strftime("%Y")
    if precision == "month":
        return dt.strftime("%m/%Y")
    if precision == "day":
        return dt.strftime("%d/%m/%Y")
    return dt.strftime("%d/%m/%Y %H:%M")


def month_key(value, precision) -> str:
    dt = parse_iso(value)
    if dt is None or precision in (None, "year", "unknown"):
        return MONTH_UNKNOWN
    return dt.strftime("%Y-%m")


def yes_no(flag) -> str:
    return "Có" if flag else "Không"


def join(items) -> str:
    return "; ".join(str(i) for i in items if i)


def url_link(url):
    return Link(url, url) if url else ""


def first_evidence(item: dict, kinds: tuple[str, ...]) -> dict | None:
    """First matching image of the newest capture (a recheck that re-shot the post wins over the original)."""
    for group in reversed(item.get("evidence_groups") or [item.get("all_evidence") or []]):
        for e in group:
            if e.get("kind") in kinds:
                return e
    return None


def main_evidence(item: dict) -> dict | None:
    return first_evidence(item, ("post",)) or first_evidence(item, ("attach", "cscroll", "comment"))


def attachments_text(attachments) -> str:
    lines = []
    for a in attachments or []:
        line = f"[{ATTACHMENT_KINDS.get(a.get('kind'), a.get('kind') or '')}] {a.get('description') or ''}".strip()
        if a.get("transcribed_text"):
            line += f"\nChữ trong ảnh: {a['transcribed_text']}"
        if a.get("url"):
            line += f"\n{a['url']}"
        lines.append(line)
    return "\n".join(lines)


def shared_text(shared) -> str:
    return join([shared.get("author_name"), shared.get("text_excerpt"), shared.get("url")]) if shared else ""


def metrics_text(metrics) -> str:
    return "; ".join(f"{METRIC_NAMES.get(k, k)}: {v}" for k, v in (metrics or {}).items()
                     if v is not None and k != "counted_at")


def issues_text(issues) -> str:
    return "; ".join(map(str, issues)) if isinstance(issues, list) else (issues or "")


def item_notes(item: dict) -> str:
    parts = [item.get("notes")]
    if item.get("supersedes"):
        parts.append(f"Thay cho {item['supersedes']}")
    if item.get("status") == "edited":
        parts.append("Đã sửa — xem sheet Lịch sử thay đổi")
    if item.get("status") == "deleted":
        parts.append("Đã bị xoá — ảnh chụp cũ vẫn giữ")
    return join(parts)


class Ctx:
    def __init__(self, project: Project, config: dict, view: View):
        self.project, self.config, self.view = project, config, view
        self.parties = {p["id"]: p for p in config.get("key_parties", [])}
        self.groups = {g["id"]: g for g in config.get("keyword_groups", [])}
        self.rows = {
            S_SOURCES: {s["id"]: i + 2 for i, s in enumerate(view.sources)},
            S_COMMENTS: {c["id"]: i + 2 for i, c in enumerate(view.comments)},
            S_CONTAINERS: {c["id"]: i + 2 for i, c in enumerate(view.containers)},
        }

    def party_label(self, pid: str) -> str:
        party = self.parties.get(pid)
        return (party.get("label") or party["name"]) if party else pid

    def parties_text(self, ids) -> str:
        return join(self.party_label(i) for i in ids or [])

    def keywords_text(self, ids) -> str:
        return join(self.groups[i]["label"] if i in self.groups else i for i in ids or [])

    def img(self, evidence: dict, width: int = 240) -> Img:
        return Img(self.project.resolve(evidence["file"]), width)

    @staticmethod
    def file_link(evidence: dict, text: str = "Mở ảnh gốc") -> Link:
        return Link("../" + evidence["file"], text)

    def internal(self, record_id):
        for sheet, rows in self.rows.items():
            if record_id in rows:
                return Internal(sheet, rows[record_id], record_id)
        return record_id or ""


def analysis_columns(ctx: Ctx) -> list[Column]:
    return [
        Column("Từ khoá", 20, lambda x: ctx.keywords_text(x.get("keywords_matched"))),
        Column("Bên được nhắc", 24, lambda x: ctx.parties_text(x.get("entities_mentioned"))),
        Column("Chủ đề", 20, lambda x: join(label("topics", t) for t in x.get("topics") or [])),
        Column("Thái độ", 10, lambda x: label("tone", x.get("tone"))),
        Column("Loại nội dung", 14, lambda x: label("claim_type", x.get("claim_type"))),
        Column("Mức quan trọng", 10, lambda x: label("importance", x.get("importance"))),
        Column("Lý do", 30, lambda x: x.get("importance_reason") or ""),
    ]


def comment_columns(ctx: Ctx) -> list[Column]:
    def own_image(c):
        e = first_evidence(c, ("comment",))
        return ctx.img(e) if e else ""

    def own_sha(c):
        e = first_evidence(c, ("comment",))
        return e.get("sha256", "") if e else ""

    def scroll(c):
        refs = c.get("scroll_refs") or []
        if not refs:
            return ""
        text = "; ".join(f"{Path(r['file']).name} (vị trí {r['position']})" for r in refs)
        return Link("../" + refs[0]["file"], text)

    return [
        Column("Mã", 12, lambda c: c["id"]),
        Column("Thuộc bài", 12, lambda c: ctx.internal(c.get("source_id"))),
        Column("Trả lời cho", 12, lambda c: ctx.internal(c["parent_comment_id"]) if c.get("parent_comment_id") else ""),
        Column("Cấp", 5, lambda c: c.get("depth")),
        Column("Ảnh riêng", 34, own_image),
        Column("Ảnh cuộn", 30, scroll),
        Column("Người viết", 20, lambda c: c.get("author_name")),
        Column("Link người viết", 28, lambda c: url_link(c.get("author_url"))),
        Column("Huy hiệu", 12, lambda c: c.get("author_badge") or ""),
        Column("Thời gian (gốc)", 14, lambda c: c.get("posted_at_raw")),
        Column("Ngày", 16, lambda c: fmt_time(c.get("posted_at"), c.get("posted_at_precision"))),
        Column("Tháng", 10, lambda c: month_key(c.get("posted_at"), c.get("posted_at_precision"))),
        Column("Nội dung nguyên văn", 60, lambda c: c.get("text")),
        Column("Đính kèm", 30, lambda c: attachments_text(c.get("attachments"))),
        Column("Thích", 8, lambda c: c["current_metrics"].get("reactions")),
        Column("Số phản hồi", 9, lambda c: c["current_metrics"].get("reply_count")),
        *analysis_columns(ctx),
        Column("Link bình luận", 30, lambda c: url_link(c.get("url"))),
        Column("Trạng thái", 12, lambda c: label("recheck_status", c["status"])),
        Column("SHA-256", 20, own_sha),
        Column("Thu thập lúc", 16, lambda c: fmt_time(c.get("captured_at"))),
        Column("Ghi chú", 30, item_notes),
    ]


def source_columns(ctx: Ctx) -> list[Column]:
    comments_col = col_letter(comment_columns(ctx), "Thuộc bài")

    def image(s):
        e = main_evidence(s)
        if e:
            return ctx.img(e)
        return NO_IMAGE if s.get("origin") == "legacy" else ""

    def image_link(s):
        e = main_evidence(s)
        return ctx.file_link(e) if e else ""

    def metric(key):
        return lambda s: s["current_metrics"].get(key)

    def snapshot(s):
        return Link("../" + s["snapshot_file"], "Mở bản chữ") if s.get("snapshot_file") else ""

    return [
        Column("Mã", 12, lambda s: s["id"]),
        Column("Nền tảng", 11, lambda s: label("platform", s.get("platform"))),
        Column("Loại", 11, lambda s: label("content_type", s.get("content_type"))),
        Column("Ảnh", 34, image),
        Column("Mở ảnh gốc", 12, image_link),
        Column("Số ảnh", 7, lambda s: len(s["all_evidence"])),
        Column("Mã nhóm", 10, lambda s: s.get("container_id") or ""),
        Column("Nhóm/Trang", 24, lambda s: s.get("container_name") or ""),
        Column("Người đăng", 20, lambda s: s.get("author_name")),
        Column("Link người đăng", 28, lambda s: url_link(s.get("author_url"))),
        Column("Loại TK", 10, lambda s: label("author_kind", s.get("author_kind"))),
        Column("Huy hiệu", 12, lambda s: s.get("author_badge") or ""),
        Column("Thời gian (gốc)", 16, lambda s: s.get("posted_at_raw")),
        Column("Ngày đăng", 16, lambda s: fmt_time(s.get("posted_at"), s.get("posted_at_precision"))),
        Column("Tháng đăng", 10, lambda s: month_key(s.get("posted_at"), s.get("posted_at_precision"))),
        Column("Độ chính xác", 14, lambda s: label("posted_at_precision", s.get("posted_at_precision"))),
        Column("Nội dung nguyên văn", 60, lambda s: s.get("text")),
        Column("Đính kèm / chữ trong ảnh", 40, lambda s: attachments_text(s.get("attachments"))),
        Column("Chia sẻ từ", 30, lambda s: shared_text(s.get("shared_from"))),
        Column("Thích", 8, metric("reactions")),
        Column("Bình luận (FB)", 10, metric("comments")),
        Column("Bình luận (đã thu)", 10,
               lambda s: Formula("=" + countif(S_COMMENTS, comments_col, countif_literal(s["id"])))),
        Column("Chia sẻ", 8, metric("shares")),
        Column("Lượt xem", 9, metric("views")),
        Column("Đếm lúc", 16, lambda s: fmt_time(s["current_metrics"].get("counted_at"))),
        *analysis_columns(ctx),
        Column("Link bài", 30, lambda s: url_link(s.get("url"))),
        Column("Loại link", 14, lambda s: label("url_kind", s.get("url_kind"))),
        Column("Trạng thái", 12, lambda s: label("recheck_status", s["status"])),
        Column("Kiểm tra lần cuối", 16, lambda s: fmt_time(s.get("last_checked_at"))),
        Column("SHA-256 ảnh chính", 20, lambda s: (main_evidence(s) or {}).get("sha256", "")),
        Column("Bản chữ gốc", 12, snapshot),
        Column("Thu thập lúc", 16, lambda s: fmt_time(s.get("captured_at"))),
        Column("Lần quét", 18, lambda s: s.get("run_id")),
        Column("Nguồn dữ liệu", 12, lambda s: label("origin", s.get("origin"))),
        Column("Ghi chú", 30, item_notes),
    ]


def container_columns(ctx: Ctx) -> list[Column]:
    group_col = col_letter(source_columns(ctx), "Mã nhóm")
    return [
        Column("Mã", 10, lambda c: c["id"]),
        Column("Tên", 30, lambda c: c.get("name")),
        Column("Loại", 8, lambda c: label("container_kind", c.get("kind"))),
        Column("Link", 30, lambda c: url_link(c.get("url"))),
        Column("Công khai/Kín", 12, lambda c: label("privacy", c.get("privacy"))),
        Column("Thành viên", 10, lambda c: c.get("member_count")),
        Column("Chuyên đề vụ việc", 10, lambda c: yes_no(c.get("topic_dedicated"))),
        Column("Đã tham gia", 14, lambda c: label("joined", c.get("joined"))),
        Column("Cách quét", 14, lambda c: label("scan_mode", c.get("scan_mode"))),
        Column("Số bài thu được", 10,
               lambda c: Formula("=" + countif(S_SOURCES, group_col, countif_literal(c["id"])))),
        Column("Quét lần cuối", 16, lambda c: fmt_time(c.get("last_scanned_at"))),
        Column("Cần xin vào", 10, lambda c: "Có" if needs_join(c) else ""),
        Column("Ghi chú", 30, lambda c: c.get("notes") or ""),
    ]


def log_columns(ctx: Ctx) -> list[Column]:
    names = {c["id"]: c.get("name") for c in ctx.view.containers}

    def scope(r):
        text = label("scope", r.get("scope"))
        cid = r.get("container_id")
        return f"{text}: {names.get(cid, cid)}" if cid else text

    return [
        Column("Mã", 12, lambda r: r["id"]),
        Column("Lần quét", 18, lambda r: r.get("run_id")),
        Column("Bắt đầu", 16, lambda r: fmt_time(r.get("started_at"))),
        Column("Kết thúc", 16, lambda r: fmt_time(r.get("ended_at"))),
        Column("Nền tảng", 11, lambda r: label("platform", r.get("platform"))),
        Column("Phạm vi", 24, scope),
        Column("Mục", 14, lambda r: label("section", r.get("section"))),
        Column("Từ khoá", 20, lambda r: r.get("query")),
        Column("Bộ lọc", 16, lambda r: json.dumps(r["filters"], ensure_ascii=False) if r.get("filters") else ""),
        Column("Đã xem", 8, lambda r: r.get("results_seen")),
        Column("Mới", 7, lambda r: r.get("results_new")),
        Column("Trùng", 7, lambda r: r.get("results_duplicate")),
        Column("Loại trừ", 8, lambda r: r.get("results_excluded")),
        Column("Hết kết quả", 9, lambda r: yes_no(r.get("reached_end"))),
        Column("Sự cố/giới hạn", 40, lambda r: issues_text(r.get("issues"))),
        Column("Ghi chú", 30, lambda r: r.get("notes") or ""),
    ]


def change_columns(ctx: Ctx) -> list[Column]:
    def notes(r):
        parts = [r.get("notes")]
        if r.get("_metrics_grew"):
            parts.append("Tương tác tăng")
        if r.get("updates"):
            parts.append("Cập nhật: " + ", ".join(f"{k}={v}" for k, v in r["updates"].items()))
        return join(parts)

    return [
        Column("Mã", 12, lambda r: r["id"]),
        Column("Đối tượng", 12, lambda r: ctx.internal(r.get("target_id"))),
        Column("Kiểm tra lúc", 16, lambda r: fmt_time(r.get("checked_at"))),
        Column("Trạng thái", 14, lambda r: label("recheck_status", r.get("status"))),
        Column("Nội dung mới", 60, lambda r: r.get("new_text") or ""),
        Column("Số liệu mới", 24, lambda r: metrics_text(r.get("metrics"))),
        Column("Ảnh", 12, lambda r: ctx.file_link(r["evidence"][0], "Mở ảnh") if r.get("evidence") else ""),
        Column("Ghi chú", 30, notes),
    ]


def exclusion_columns() -> list[Column]:
    return [
        Column("Mã", 12, lambda r: r["id"]),
        Column("Thời điểm", 16, lambda r: fmt_time(r.get("recorded_at"))),
        Column("Link", 40, lambda r: url_link(r.get("url"))),
        Column("Trích đoạn", 50, lambda r: r.get("excerpt")),
        Column("Từ khoá khớp", 20, lambda r: join(r.get("keywords_matched") or [])),
        Column("Lý do", 40, lambda r: r.get("reason")),
    ]


def write_data_sheets(wb, ctx: Ctx) -> tuple[list[Column], list[Column], list[Column]]:
    view, thumbs = ctx.view, ctx.project.thumbs_dir
    src_cols, cmt_cols, ctr_cols = source_columns(ctx), comment_columns(ctx), container_columns(ctx)
    write_table(wb[S_SOURCES], src_cols, view.sources, thumbs)
    write_table(wb[S_COMMENTS], cmt_cols, view.comments, thumbs)
    write_table(wb[S_CONTAINERS], ctr_cols, view.containers, thumbs,
                fill=lambda c: YELLOW_FILL if needs_join(c) else None)
    write_table(wb[S_LOG], log_columns(ctx), view.search_logs, thumbs)
    write_table(wb[S_CHANGES], change_columns(ctx), view.changes, thumbs)
    write_table(wb[S_EXCLUDED], exclusion_columns(), view.exclusions, thumbs)
    return src_cols, cmt_cols, ctr_cols


def timeline_columns(ctx: Ctx) -> list[Column]:
    def related(e):
        ids = e.get("related_ids") or []
        if not ids:
            return ""
        link = ctx.internal(ids[0])
        if isinstance(link, Internal):
            link.text = join(ids)
            return link
        return join(ids)

    return [
        Column("Mã", 10, lambda e: e["id"]),
        Column("Ngày", 16, lambda e: e.get("date_raw")),
        Column("Sự kiện", 70, lambda e: e.get("description")),
        Column("Nguồn", 30, lambda e: e.get("source_text") or ""),
        Column("Mã liên quan", 14, related),
        Column("Độ tin cậy", 22, lambda e: label("reliability", e.get("reliability"))),
    ]


def people_items(ctx: Ctx) -> list[dict]:
    everything = ctx.view.sources + ctx.view.comments
    items: list[dict] = []
    for party in ctx.config.get("key_parties", []):
        mentions = [x for x in everything if party["id"] in (x.get("entities_mentioned") or [])]
        dates = sorted(x["posted_at"] for x in mentions if x.get("posted_at"))
        items.append({"row_kind": "party", "name": party["name"], "label": ctx.party_label(party["id"]),
                      "group": "Bên chính" if party.get("primary") else "Bên liên quan khác",
                      "kind": party.get("kind", ""), "url": "", "role": party.get("role", ""),
                      "first": dates[0] if dates else None, "last": dates[-1] if dates else None,
                      "platforms": sorted({x["platform"] for x in mentions if x.get("platform")})})
    authors: dict[str, dict] = {}
    for x in everything:
        key = x.get("author_url") or "name:" + (x.get("author_name") or "")
        author = authors.setdefault(key, {"row_kind": "author", "name": x.get("author_name") or "",
                                          "url": x.get("author_url") or "",
                                          "kind": label("author_kind", x.get("author_kind")), "role": "",
                                          "posts": 0, "dates": [], "platforms": set()})
        if x["record_type"] == "source":
            author["posts"] += 1
        if x.get("posted_at"):
            author["dates"].append(x["posted_at"])
        if x.get("platform"):
            author["platforms"].add(x["platform"])
    for author in authors.values():
        dates = sorted(author.pop("dates"))
        author.update(group="Người đăng" if author["posts"] else "Người bình luận",
                      first=dates[0] if dates else None, last=dates[-1] if dates else None,
                      platforms=sorted(author["platforms"]))
        items.append(author)
    return items


def people_columns(ctx: Ctx, src_cols: list[Column], cmt_cols: list[Column]) -> list[Column]:
    def by_author(sheet, cols, url_header, name_header, p):
        if p["url"]:
            return countif(sheet, col_letter(cols, url_header), countif_literal(p["url"]))
        return countif(sheet, col_letter(cols, name_header), countif_literal(p["name"]))

    def posts(p):
        if p["row_kind"] == "party":
            return ""
        return Formula("=" + by_author(S_SOURCES, src_cols, "Link người đăng", "Người đăng", p))

    def comments(p):
        if p["row_kind"] == "party":
            return ""
        return Formula("=" + by_author(S_COMMENTS, cmt_cols, "Link người viết", "Người viết", p))

    def mentions(p):
        if p["row_kind"] != "party":
            return ""
        crit = f"*{countif_literal(p['label'])}*"
        return Formula("=" + countif(S_SOURCES, col_letter(src_cols, "Bên được nhắc"), crit) + "+"
                       + countif(S_COMMENTS, col_letter(cmt_cols, "Bên được nhắc"), crit))

    return [
        Column("Tên", 30, lambda p: p["name"]),
        Column("Nhóm", 16, lambda p: p["group"]),
        Column("Loại", 14, lambda p: p["kind"]),
        Column("Link", 30, lambda p: url_link(p["url"])),
        Column("Vai trò", 50, lambda p: p["role"]),
        Column("Số bài đăng", 9, posts),
        Column("Số bình luận", 9, comments),
        Column("Số lần được nhắc", 10, mentions),
        Column("Xuất hiện lần đầu", 16, lambda p: fmt_time(p["first"], "day")),
        Column("Lần gần nhất", 16, lambda p: fmt_time(p["last"], "day")),
        Column("Nền tảng", 14, lambda p: join(label("platform", x) for x in p["platforms"])),
    ]


def evidence_items(ctx: Ctx) -> list[dict]:
    items = []
    for x in ctx.view.sources + ctx.view.comments:
        if x.get("importance") != "cao":
            continue
        e = first_evidence(x, ("comment",)) if x["record_type"] == "comment" else main_evidence(x)
        items.append({**x, "_evidence": e})
    return items


def evidence_columns(ctx: Ctx) -> list[Column]:
    def summary(x):
        text = x.get("text") or ""
        return text if len(text) <= 300 else text[:300] + "…"

    return [
        Column("Mã", 12, lambda x: ctx.internal(x["id"])),
        Column("Loại", 10, lambda x: "Bình luận" if x["record_type"] == "comment" else "Bài viết"),
        Column("Ảnh", 64, lambda x: ctx.img(x["_evidence"], 480) if x["_evidence"] else NO_IMAGE),
        Column("Tóm tắt nội dung", 50, summary),
        Column("Người đăng", 20, lambda x: x.get("author_name")),
        Column("Link", 30, lambda x: url_link(x.get("url"))),
        Column("Thời gian", 18, lambda x: join([x.get("posted_at_raw"),
                                                fmt_time(x.get("posted_at"), x.get("posted_at_precision"))])),
        Column("Lý do quan trọng", 30, lambda x: x.get("importance_reason") or ""),
        Column("File ảnh gốc", 30,
               lambda x: ctx.file_link(x["_evidence"], x["_evidence"]["file"]) if x["_evidence"] else ""),
        Column("SHA-256", 20, lambda x: (x["_evidence"] or {}).get("sha256", "")),
        Column("Thu thập lúc", 16, lambda x: fmt_time(x.get("captured_at"))),
    ]


def write_overview(ws, ctx: Ctx, src_cols, cmt_cols, ctr_cols) -> None:
    view = ctx.view
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 70
    row = 1

    def put(text, value=None, note=None, font=None):
        nonlocal row
        write_cell(ws, row, 1, text)
        if font is not None:
            ws.cell(row, 1).font = font
        if value is not None:
            write_cell(ws, row, 2, value)
            ws.cell(row, 2).font = BOLD
        if note:
            write_cell(ws, row, 3, note)
        row += 1

    def section(title):
        nonlocal row
        row += 1
        put(title, font=BOLD)
        for c in (1, 2, 3):
            ws.cell(row - 1, c).fill = SECTION_FILL
            ws.cell(row - 1, c).border = BORDER

    def both(src_header, cmt_header, criterion):
        return Formula("=" + countif(S_SOURCES, col_letter(src_cols, src_header), criterion) + "+"
                       + countif(S_COMMENTS, col_letter(cmt_cols, cmt_header), criterion))

    put(f"TỔNG HỢP NHẮC ĐẾN VỤ VIỆC {ctx.config.get('project_name', '').upper()}", font=TITLE_FONT)
    put("Cập nhật lúc", fmt_time(now_iso()))
    runs = sorted({r["run_id"] for r in view.sources + view.search_logs
                   if r.get("run_id") and r.get("origin") != "legacy"})
    put("Lần quét gần nhất", runs[-1] if runs else "Chưa quét")

    section("Mục lục — bấm tên sheet để mở")
    for name in SHEET_ORDER[1:]:
        put(Internal(name, 1, name), None, SHEET_DESCRIPTIONS[name])

    section("Tổng số")
    put("Bài viết & nguồn", Formula(f"=COUNTA('{S_SOURCES}'!A:A)-1"))
    put("Bình luận", Formula(f"=COUNTA('{S_COMMENTS}'!A:A)-1"))
    put("Nhóm & trang", Formula(f"=COUNTA('{S_CONTAINERS}'!A:A)-1"))
    put("Nhóm kín cần xin vào", Formula("=" + countif(S_CONTAINERS, col_letter(ctr_cols, "Cần xin vào"), "Có")))
    put("Kết quả đã loại trừ (trùng tên)", Formula(f"=COUNTA('{S_EXCLUDED}'!A:A)-1"))

    section("Nguồn theo nền tảng")
    for platform in PLATFORMS:
        text = label("platform", platform)
        put(text, Formula("=" + countif(S_SOURCES, col_letter(src_cols, "Nền tảng"), countif_literal(text))))

    section("Số lần được nhắc (bài + bình luận)")
    for party in ctx.config.get("key_parties", []):
        text = ctx.party_label(party["id"])
        put(text, both("Bên được nhắc", "Bên được nhắc", f"*{countif_literal(text)}*"),
            "Bên chính" if party.get("primary") else "Bên liên quan khác")

    section("Theo thái độ (bài + bình luận)")
    for text in LABELS["tone"].values():
        put(text, both("Thái độ", "Thái độ", countif_literal(text)))

    section("Theo mức quan trọng (bài + bình luận)")
    for text in LABELS["importance"].values():
        put(text, both("Mức quan trọng", "Mức quan trọng", countif_literal(text)))

    section("Theo tháng đăng (bài + bình luận)")
    months = sorted({month_key(x.get("posted_at"), x.get("posted_at_precision"))
                     for x in view.sources + view.comments} - {MONTH_UNKNOWN})
    for month in months + [MONTH_UNKNOWN]:
        put(month, both("Tháng đăng", "Tháng", month))

    section("Chưa quét được / giới hạn")
    gaps = [r for r in view.search_logs if r.get("issues") or not r.get("reached_end")]
    if not gaps:
        put("Không có ghi nhận")
    for r in gaps[-50:]:
        put(f"{r['id']} · {label('section', r.get('section'))} · {r.get('query', '')}", None,
            issues_text(r.get("issues")) or "Chưa cuộn tới hết kết quả")


def write_legend(ws, ctx: Ctx) -> None:
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 110
    rows = [("CHÚ THÍCH", ""),
            ("Cách đọc mã", "FB-P = bài Facebook · FB-C = bình luận Facebook · FB-G = nhóm/trang Facebook · "
                            "WEB-P = bài báo/website · LOG = nhật ký quét · CHK = lần kiểm tra lại · "
                            "EXC = kết quả đã loại trừ · EVT = mốc sự kiện")]
    for enum_name, title in (("tone", "Thái độ"), ("claim_type", "Loại nội dung"), ("importance", "Mức quan trọng")):
        rows.append((title, ""))
        for key, text in LABELS[enum_name].items():
            rows.append((f"   {text}", DESCRIPTIONS[enum_name][key]))
    rows += [
        ("Loại link", "Link riêng của bài = mở thẳng tới bài · Chỉ có link nhóm = Facebook không cho lấy link "
                      "riêng, phải tìm bài trong nhóm · Không có link"),
        ("Độ chính xác thời gian", "Chính xác = lấy từ ô hiện ra khi rê chuột lên mốc thời gian · Ước lượng = "
                                   "quy đổi từ \"2 giờ\", \"3 ngày\"… theo thời điểm thu thập"),
        ("Ảnh cuộn", "Ảnh chụp liên tiếp phần bình luận; cột ghi tên file và bình luận nằm ở vị trí thứ mấy trong ảnh"),
        ("Trạng thái", "Còn · Đã sửa (nội dung mới ở sheet Lịch sử thay đổi, nội dung cũ vẫn giữ) · Đã xoá · "
                       "Không truy cập được"),
        ("Kiểm tra ảnh không bị sửa", "Mở Command Prompt, chạy: certutil -hashfile \"<đường dẫn ảnh>\" SHA256 — "
                                      "kết quả phải trùng cột SHA-256"),
        ("Chuyển file sang máy khác", "Phải chép cả thư mục dự án (gồm screenshots, snapshots, output) — "
                                      "link ảnh là đường dẫn tương đối"),
        ("Lưu ý ngôn từ", "Nội dung nguyên văn giữ nguyên lời người đăng. Các từ như \"lừa đảo\" là cách người đăng "
                          "gọi, không phải kết luận pháp lý. Phân loại thái độ/cáo buộc chỉ mô tả nội dung."),
    ]
    for r, (a, b) in enumerate(rows, 1):
        write_cell(ws, r, 1, a)
        write_cell(ws, r, 2, b)
        if r > 1:
            for c in (1, 2):
                ws.cell(r, c).border = BORDER
            if b:
                ws.cell(r, 1).font = BOLD
            else:
                for c in (1, 2):
                    ws.cell(r, c).fill = SECTION_FILL
                ws.cell(r, 1).font = BOLD
    ws.cell(1, 1).font = TITLE_FONT


def write_summary_sheets(wb, ctx: Ctx, src_cols, cmt_cols, ctr_cols) -> None:
    thumbs = ctx.project.thumbs_dir
    write_table(wb[S_TIMELINE], timeline_columns(ctx), ctx.view.events, thumbs)
    write_table(wb[S_PEOPLE], people_columns(ctx, src_cols, cmt_cols), people_items(ctx), thumbs)
    write_table(wb[S_EVIDENCE], evidence_columns(ctx), evidence_items(ctx), thumbs)
    write_overview(wb[S_OVERVIEW], ctx, src_cols, cmt_cols, ctr_cols)
    write_legend(wb[S_LEGEND], ctx)
    for name in (S_OVERVIEW, S_LEGEND):
        setup_print(wb[name])
    for name, color in TAB_COLORS.items():
        wb[name].sheet_properties.tabColor = color


def build(project: Project) -> dict:
    config = project.load_config()
    records, warnings = read_records(project.records_path)
    view = build_view(records, warnings)
    ctx = Ctx(project, config, view)
    wb = Workbook()
    wb.remove(wb.active)
    for name in SHEET_ORDER:
        wb.create_sheet(name)
    src_cols, cmt_cols, ctr_cols = write_data_sheets(wb, ctx)
    write_summary_sheets(wb, ctx, src_cols, cmt_cols, ctr_cols)
    wb.calculation.fullCalcOnLoad = True
    for ws in wb.worksheets:
        view.warnings.extend(sheet_warnings(ws))

    out = project.output_path(config)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".tmp.xlsx")
    wb.save(tmp)
    try:
        os.replace(tmp, out)
    except PermissionError as exc:
        tmp.unlink(missing_ok=True)
        raise ExcelLockedError(f"Không ghi được {out.name}: file đang mở (thường là trong Excel). "
                               "Đóng file rồi chạy lại.") from exc
    counts = {"sources": len(view.sources), "comments": len(view.comments), "containers": len(view.containers),
              "search_logs": len(view.search_logs), "changes": len(view.changes),
              "exclusions": len(view.exclusions), "events": len(view.events)}
    return {"status": "ok", "file": str(out), "counts": counts, "warnings": view.warnings}


def main(argv: list[str] | None = None) -> int:
    setup_stdout()
    parser = argparse.ArgumentParser(description="Dựng file Excel tổng hợp từ data/records.jsonl")
    parser.add_argument("--project", help="thư mục dự án (mặc định: thư mục chứa .claude)")
    args = parser.parse_args(argv)
    project = Project(args.project) if args.project else Project()
    try:
        result = build(project)
    except ExcelLockedError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
