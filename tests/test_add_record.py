import hashlib
import json

import add_record
from add_record import add_records, check
from common import read_records
from factories import ev, fb_comment, fb_container, fb_source

RUN = "RUN-2026-09-29-01"


def add(project, recs):
    return add_records(project, recs if isinstance(recs, list) else [recs], RUN, project.load_config())


def _legacy(**over):
    rec = fb_source([], origin="legacy", tone=None, claim_type=None, importance_reason=None, **over)
    rec.pop("snapshot_text")
    return rec


def _source_with_scrolls(project, make_png, n=2):
    shots = [ev(make_png("post.png"))] + [
        ev(make_png(f"cs{i}.png"), kind="cscroll", shows=f"Bình luận phần {i}") for i in range(1, n + 1)]
    [res] = add(project, fb_source(shots))
    return res["id"], [p for p in res["evidence_paths"] if "_cscroll_" in p]


def test_add_source_copies_evidence_and_hashes(project, make_png):
    shot = make_png("tmp_a.png")
    [res] = add(project, fb_source([ev(shot), ev(make_png("tmp_b.png", color=(0, 0, 255)), "attach", "Giấy mời")]))
    assert res["status"] == "added" and res["id"] == "FB-P00001"
    [rec], _ = read_records(project.records_path)
    names = [e["file"].split("/")[-1] for e in rec["evidence"]]
    assert names == ["FB-P00001_post_01.png", "FB-P00001_attach_01.png"]
    stored = project.resolve(rec["evidence"][0]["file"])
    assert stored.is_file() and shot.is_file()  # file tạm không bị xoá
    assert rec["evidence"][0]["sha256"] == hashlib.sha256(stored.read_bytes()).hexdigest()
    assert rec["evidence"][0]["file"].startswith("screenshots/facebook/")
    assert res["evidence_paths"] == [e["file"] for e in rec["evidence"]]
    assert "snapshot_text" not in rec
    assert project.resolve(rec["snapshot_file"]).read_text(encoding="utf-8").startswith("Quyết Chiến")
    assert len(rec["snapshot_sha256"]) == 64
    assert rec["run_id"] == RUN and rec["origin"] == "scan" and rec["dedupe_key"].startswith("url:")


def test_duplicate_is_reported_and_store_unchanged(project, make_png):
    add(project, fb_source([ev(make_png())]))
    before = project.records_path.read_bytes()
    variant = fb_source([ev(make_png("again.png"))],
                        url="https://m.facebook.com/groups/427692059062534/posts/1597546225410439/?__tn__=R")
    assert add(project, variant) == [{"index": 0, "status": "duplicate", "existing_id": "FB-P00001"}]
    assert project.records_path.read_bytes() == before


def test_scan_supersedes_legacy(project, make_png):
    add(project, _legacy())
    [res] = add(project, fb_source([ev(make_png())]))
    assert res["status"] == "added" and res["id"] == "FB-P00002" and res["supersedes"] == "FB-P00001"
    [again] = add(project, fb_source([ev(make_png("x2.png"))]))
    assert again["status"] == "duplicate" and again["existing_id"] == "FB-P00002"


def test_manual_supersedes_must_point_to_legacy(project, make_png):
    [res] = add(project, fb_source([ev(make_png())], supersedes="FB-P00077"))
    assert res["status"] == "invalid" and "có trong kho" in res["errors"][0]


def test_comment_tree_with_batch_refs(project, make_png):
    sid, scrolls = _source_with_scrolls(project, make_png)
    res = add(project, [
        fb_comment(sid, scrolls[0], 1, text="Bình luận gốc"),
        fb_comment(sid, scrolls[0], 2, text="Trả lời 1", depth=2, parent_comment_id="@0"),
        fb_comment(sid, scrolls[1], 1, text="Trả lời 2", depth=3, parent_comment_id="@1"),
    ])
    assert [r["status"] for r in res] == ["added"] * 3
    records, _ = read_records(project.records_path)
    by_id = {r["id"]: r for r in records}
    assert res[0]["id"] == "FB-C000001"
    assert by_id[res[1]["id"]]["parent_comment_id"] == res[0]["id"]
    assert by_id[res[2]["id"]]["parent_comment_id"] == res[1]["id"]
    assert by_id[res[0]["id"]]["platform"] == "facebook"


def test_invalid_parent_invalidates_children_but_not_siblings(project, make_png):
    sid, scrolls = _source_with_scrolls(project, make_png)
    res = add(project, [
        fb_comment(sid, scrolls[0], 1, tone="sai"),
        fb_comment(sid, scrolls[0], 2, depth=2, parent_comment_id="@0", text="con"),
        fb_comment(sid, scrolls[1], 1, text="bình luận độc lập"),
    ])
    assert [r["status"] for r in res] == ["invalid", "invalid", "added"]
    assert "không hợp lệ nên" in res[1]["errors"][0]


def test_scroll_refs_must_be_canonical_cscroll_of_source(project, make_png):
    sid, scrolls = _source_with_scrolls(project, make_png)
    [res] = add(project, fb_comment(sid, str(make_png("cs1.png"))))  # đường dẫn tạm, không phải đường dẫn chuẩn
    assert res["status"] == "invalid" and "evidence_paths" in res["errors"][0]
    [res] = add(project, fb_comment(sid, scrolls[0].replace("/", "\\")))  # dấu \ vẫn được chấp nhận
    assert res["status"] == "added"


def test_missing_evidence_file_is_invalid_not_crash(project, tmp_path):
    [res] = add(project, fb_source([ev(tmp_path / "không tồn tại" / "shot.png")]))
    assert res["status"] == "invalid" and "Không tìm thấy file ảnh" in res["errors"][0]
    assert not project.records_path.exists()


def test_evidence_path_with_spaces_backslashes_and_vietnamese(project, make_png):
    shot = make_png("ảnh chụp 1.png")
    [res] = add(project, fb_source([ev(str(shot).replace("/", "\\"))]))
    assert res["status"] == "added"
    assert res["evidence_paths"][0].endswith("FB-P00001_post_01.png")


def test_identical_short_comments_kept_and_rerun_dedupes(project, make_png):
    sid, scrolls = _source_with_scrolls(project, make_png)
    batch = [fb_comment(sid, scrolls[0], 1, text="+1"), fb_comment(sid, scrolls[0], 2, text="+1")]
    assert [r["status"] for r in add(project, batch)] == ["added", "added"]
    assert [r["status"] for r in add(project, batch)] == ["duplicate", "duplicate"]


def test_recheck_evidence_extends_allowed_scrolls(project, make_png):
    sid, _ = _source_with_scrolls(project, make_png, n=1)
    [chk] = add(project, {"record_type": "recheck", "target_id": sid, "checked_at": "2026-10-10T20:00:00+07:00",
                          "status": "active", "metrics": {"reactions": 9},
                          "evidence": [ev(make_png("new_cs.png"), "cscroll", "Bình luận mới")]})
    assert chk["id"] == "CHK-000001"
    [c] = add(project, fb_comment(sid, chk["evidence_paths"][0], text="Bình luận mới"))
    assert c["status"] == "added"


def test_unknown_reference_ids(project):
    [res] = add(project, {"record_type": "recheck", "target_id": "FB-P09999",
                          "checked_at": "2026-10-10T20:00:00+07:00", "status": "deleted"})
    assert res["status"] == "invalid" and "FB-P09999" in res["errors"][0]


def test_container_reference(project, make_png):
    [ctr] = add(project, fb_container())
    assert ctr["id"] == "FB-G0001"
    [ok] = add(project, fb_source([ev(make_png())], container_id="FB-G0001"))
    [bad] = add(project, fb_source([ev(make_png("b.png"))], url="https://www.facebook.com/groups/1/posts/9",
                                   container_id="FB-G0099"))
    assert ok["status"] == "added" and bad["status"] == "invalid"


def test_check_by_url_text_and_key(project, make_png):
    add(project, fb_source([ev(make_png())]))
    assert check(project, url="https://m.facebook.com/groups/427692059062534/posts/1597546225410439?__tn__=x")["found"]
    assert check(project, text="to chuc cuoc hop giua cu dan")["matches"][0]["id"] == "FB-P00001"
    assert not check(project, url="https://www.facebook.com/groups/1/posts/2")["found"]
    assert check(project, record=fb_source([]))["found"]


def test_cli_add_and_check(project, make_png, tmp_path, capsys):
    payload = tmp_path / "rec.json"
    payload.write_text(json.dumps(fb_source([ev(make_png())]), ensure_ascii=False), encoding="utf-8")
    assert add_record.main(["--project", str(project.root), "add", "--run", RUN, "--json", str(payload)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["status"] == "added"
    assert add_record.main(["--project", str(project.root), "check", "--text", "Roxana Plaza"]) == 0
    assert json.loads(capsys.readouterr().out)["found"] is True
