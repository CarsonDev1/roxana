import json

import pytest

from add_record import add_records
from bundle_to_records import apply_bundle, parse_tooltip, drafts
from common import read_records

RUN = "RUN-2026-10-01-01"


@pytest.mark.parametrize("tip, iso", [
    ("Thứ Hai, 7 Tháng 9, 2026 lúc 13:14", "2026-09-07T13:14:00+07:00"),
    ("Thứ bảy, 22 Tháng 8, 2026 lúc 09:05", "2026-08-22T09:05:00+07:00"),
    ("Chủ Nhật, 1 Tháng 12, 2024 lúc 0:07", "2024-12-01T00:07:00+07:00"),
    ("Monday, September 7, 2026 at 1:14 PM", "2026-09-07T13:14:00+07:00"),
    ("Sunday, December 1, 2024 at 12:07 AM", "2024-12-01T00:07:00+07:00"),
])
def test_parse_tooltip(tip, iso):
    assert parse_tooltip(tip) == iso


def test_parse_tooltip_unknown():
    assert parse_tooltip(None) is None and parse_tooltip("5 tuần") is None


def _bundle(tmp_path, make_png):
    b = tmp_path / "bundles" / "1611357984029263"
    b.mkdir(parents=True)
    for name in ("p_post_01.png", "p_post_02.png", "p_cscroll_01.png", "p_cscroll_02.png", "attach_01.png"):
        (b / name).write_bytes(make_png(name).read_bytes())
    (b / "p_snapshot.txt").write_text("Bài viết của A\nNội dung...", encoding="utf-8")
    (b / "feed.json").write_text(json.dumps({
        "permalink": "https://www.facebook.com/groups/427692059062534/posts/1611357984029263/",
        "tooltip": "Thứ Hai, 7 Tháng 9, 2026 lúc 13:14", "author": "Anh Bac Ho Le",
        "message": "Roxana Plaza lại trễ hẹn", "media": [], "image_alts": []}, ensure_ascii=False), encoding="utf-8")
    (b / "p_comments.json").write_text(json.dumps([
        {"author": "B", "author_href": "https://www.facebook.com/groups/427692059062534/user/1/?__cft__[0]=x",
         "time_text": "5 tuần", "comment_url": "https://www.facebook.com/groups/427692059062534/posts/1611357984029263/?comment_id=11",
         "fb_comment_id": "11", "parent_fb_comment_id": None, "text": "Trả nhà đi", "emoji": [], "stickers": [], "depth": 1,
         "reacts": ["3 cảm xúc; xem ai đã bày tỏ cảm xúc về bình luận này"]},
        {"author": "C", "author_href": "https://www.facebook.com/groups/427692059062534/user/2/",
         "time_text": "5 tuần", "comment_url": "https://www.facebook.com/x/?comment_id=11&reply_comment_id=22",
         "fb_comment_id": "22", "parent_fb_comment_id": "11", "text": "", "emoji": ["❤️", "👍"], "stickers": [], "depth": 2,
         "reacts": []},
    ], ensure_ascii=False), encoding="utf-8")
    (b / "times.json").write_text(json.dumps([
        {"fb_comment_id": "11", "tooltip": "Chủ Nhật, 23 Tháng 8, 2026 lúc 15:14"},
        {"fb_comment_id": "22", "tooltip": None}], ensure_ascii=False), encoding="utf-8")
    (b / "log.json").write_text(json.dumps({
        "started_at": "2026-09-30T11:20:00+07:00", "ended_at": "2026-09-30T11:20:30+07:00",
        "post": {"author": "Anh Bac Ho Le", "author_href": "https://www.facebook.com/groups/427692059062534/user/9/?__cft__[0]=q",
                 "text": "Roxana Plaza lại trễ hẹn — bản đầy đủ", "time_text": "7 Tháng 9",
                 "metrics": {"reactions": 12, "comments": 2, "shares": 1}},
        "filter": "Tất cả bình luận",
        "steps": [{"shot": str(b / "p_post_01.png"), "kind": "post", "shows": "Khung bài", "at": "11:20:01"},
                  {"shot": str(b / "p_post_02.png"), "kind": "post", "shows": "Phần dưới", "at": "11:20:03"},
                  {"shot": str(b / "p_cscroll_01.png"), "kind": "cscroll", "shows": "Bình luận đoạn 1", "at": "11:20:10",
                   "comments": ["11"]},
                  {"shot": str(b / "p_cscroll_02.png"), "kind": "cscroll", "shows": "Bình luận đoạn 2", "at": "11:20:12",
                   "comments": ["11", "22"]}],
        "attachments": [{"file": str(b / "attach_01.png"), "url": "https://www.facebook.com/photo/?fbid=5", "alt": "văn bản"}],
    }, ensure_ascii=False), encoding="utf-8")
    return b


def test_drafts_fill_mechanical_fields(project, tmp_path, make_png):
    b = _bundle(tmp_path, make_png)
    d = drafts(b, container_id="FB-G0001", container_name="ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ")
    s = d["source"]
    assert s["url"].endswith("/posts/1611357984029263/") and s["url_kind"] == "permalink"
    assert s["posted_at"] == "2026-09-07T13:14:00+07:00" and s["posted_at_precision"] == "exact"
    assert s["posted_at_raw"] == "7 Tháng 9" and s["text"].endswith("bản đầy đủ")
    assert s["metrics"]["reactions"] == 12 and s["metrics"]["counted_at"] == "2026-09-30T11:20:03+07:00"
    assert [e["kind"] for e in s["evidence"]] == ["post", "post", "attach", "cscroll", "cscroll"]
    assert s["captured_at"] == "2026-09-30T11:20:00+07:00" and s["snapshot_file"].endswith("p_snapshot.txt")
    c1, c2 = d["comments"]
    assert c1["posted_at"] == "2026-08-23T15:14:00+07:00" and c1["posted_at_precision"] == "exact"
    assert c1["reactions"] == 3 and c1["scroll_refs"] == [{"cscroll": 1, "position": 1}, {"cscroll": 2, "position": 1}]
    assert c2["depth"] == 2 and c2["parent_comment_id"] == "@0" and c2["text"] == "❤️👍"
    assert c2["posted_at_precision"] == "relative_estimate" and c2["posted_at"].startswith("2026-08-")
    assert d["classify"]["source"]["text"].endswith("bản đầy đủ") and d["classify"]["comments"][1]["fb_comment_id"] == "22"


def test_apply_bundle_writes_source_and_comment_tree(project, tmp_path, make_png):
    b = _bundle(tmp_path, make_png)
    cls = {"source": {"tone": "tieu_cuc", "claim_type": "y_kien", "importance": "trung_binh",
                      "importance_reason": "Ý kiến cụ thể", "topics": ["cham_ban_giao"], "entities_mentioned": ["tuongphong"]},
           "comments": {"11": {"tone": "tieu_cuc", "claim_type": "y_kien", "importance": "thap", "topics": [],
                               "entities_mentioned": []},
                        "22": {"tone": "tich_cuc", "claim_type": "y_kien", "importance": "thap", "topics": [],
                               "entities_mentioned": []}}}
    res = apply_bundle(project, b, cls, RUN, container_id=None, container_name="ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ")
    assert res["source"]["status"] == "added" and [c["status"] for c in res["comments"]] == ["added", "added"]
    records, _ = read_records(project.records_path)
    src = next(r for r in records if r["record_type"] == "source")
    cm = [r for r in records if r["record_type"] == "comment"]
    assert src["keywords_matched"] == ["roxana"]
    assert cm[1]["parent_comment_id"] == cm[0]["id"]
    assert cm[0]["scroll_refs"][0]["file"].endswith("_cscroll_01.png")
    again = apply_bundle(project, b, cls, RUN, container_id=None, container_name="ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ")
    assert again["source"]["status"] == "duplicate"


def test_apply_rejects_missing_classification(project, tmp_path, make_png):
    b = _bundle(tmp_path, make_png)
    with pytest.raises(ValueError):
        apply_bundle(project, b, {"source": {}, "comments": {}}, RUN, container_id=None, container_name="X")


@pytest.mark.parametrize("raw, n_comments, expected", [
    (["422", "111", "30"], 100, {"reactions": 422, "comments": 111, "shares": 30}),
    (["61"], 0, {"reactions": 61, "comments": None, "shares": None}),
    (["2,5K", "3"], 3, {"reactions": 2500, "comments": 3, "shares": None}),
    (["12", "4"], 0, {"reactions": 12, "comments": None, "shares": 4}),
    ([], 0, {"reactions": None, "comments": None, "shares": None}),
])
def test_counts_from_raw(raw, n_comments, expected):
    from bundle_to_records import counts
    assert counts(raw, n_comments) == expected


def test_shared_post_becomes_shared_from(project, tmp_path, make_png):
    b = _bundle(tmp_path, make_png)
    log = json.loads((b / "log.json").read_text(encoding="utf-8"))
    log["post"] = {"author": "Tulip Hoa", "author_href": "https://www.facebook.com/groups/1/user/5/", "text": "Mọi người xem",
                   "time_text": "3 tuần", "counts_raw": ["24", "5", "4"],
                   "shared": {"author": "Nguyen Toan Roxana", "author_href": "https://www.facebook.com/groups/1/user/6/",
                              "text": "CĐT đang tiến hành kiện các khách hàng"}}
    (b / "log.json").write_text(json.dumps(log, ensure_ascii=False), encoding="utf-8")
    s = drafts(b)["source"]
    assert s["content_type"] == "shared_post" and s["shared_from"]["author_name"] == "Nguyen Toan Roxana"
    assert s["metrics"]["shares"] == 4 and "CĐT đang tiến hành" in s["shared_from"]["text_excerpt"]
