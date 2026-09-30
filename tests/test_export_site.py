import json

import export_site
from add_record import add_records
from export_site import SCHEMA_VERSION, export
from test_build_excel import RUN, populated  # noqa: F401  (fixture)


def _data(project):
    result = export(project)
    return result, json.loads((project.root / "output" / "site" / "data.json").read_text(encoding="utf-8"))


def test_top_level_keys_and_version(populated):
    project, *_ = populated
    result, data = _data(project)
    assert result["status"] == "ok" and data["schema_version"] == SCHEMA_VERSION
    for key in ("generated_at", "project_name", "labels", "descriptions", "parties", "keyword_groups", "sources",
                "comments", "containers", "events", "search_logs", "changes", "exclusions", "people", "stats",
                "evidence", "warnings"):
        assert key in data, key


def test_sources_have_latest_state_and_hide_superseded(populated):
    project, src, _ = populated
    _, data = _data(project)
    ids = [s["id"] for s in data["sources"]]
    assert src["id"] in ids and "FB-P00002" in ids
    s = next(x for x in data["sources"] if x["id"] == src["id"])
    assert s["status"] == "edited" and s["current_text"] == "Nội dung đã sửa"
    assert s["metrics"]["reactions"] == 50 and s["comments_collected"] == 3
    assert s["main_image"]["file"] == src["evidence_paths"][0] and s["main_image"]["sha256"]
    assert s["main_image"]["thumb"].startswith("output/thumbs/")
    assert (project.root / s["main_image"]["thumb"]).is_file()
    assert s["month"] == "2026-08" and "roxana" in s["search"]


def test_comments_in_tree_order_with_depth(populated):
    project, src, comments = populated
    _, data = _data(project)
    cs = data["comments"]
    assert [c["id"] for c in cs] == [c["id"] for c in comments]
    assert cs[1]["depth"] == 2 and cs[1]["parent_comment_id"] == cs[0]["id"]
    assert cs[0]["text"] == "=))) trả nhà đi"
    assert cs[2]["text"] == "Ký tự lạ\x0b\x00 ở đây"  # JSON giữ nguyên văn; web tự hiển thị an toàn
    assert cs[1]["own_image"]["file"].endswith("_comment_01.png")
    assert cs[0]["scroll_refs"][0]["file"].endswith("_cscroll_01.png")


def test_stats_match_view(populated):
    project, *_ = populated
    _, data = _data(project)
    st = data["stats"]
    assert st["totals"] == {"sources": 2, "comments": 3, "containers": 1, "need_join": 1, "exclusions": 1,
                            "high": 2, "events": 1}
    assert st["by_platform"]["facebook"] == 2
    assert st["by_tone"]["gay_gat"] == 2 and st["by_importance"]["cao"] == 2
    months = {m["month"]: m["count"] for m in st["by_month"]}
    assert months["2026-08"] == 1 and months["2024-12"] == 1 and months["2026-09"] == 3
    assert st["by_party"]["lien"] == 2
    assert st["latest_run"] == RUN
    assert any("Facebook chỉ trả 40 kết quả" in g["issue"] for g in st["gaps"])


def test_people_containers_evidence_changes(populated):
    project, src, comments = populated
    _, data = _data(project)
    diem = next(p for p in data["people"] if p["name"] == "Huynh Bich Diem")
    assert diem["posts"] == 1 and diem["comments"] == 3
    assert data["containers"][0]["needs_join"] and data["containers"][0]["source_count"] == 1
    assert [e["id"] for e in data["evidence"]] == [src["id"], comments[1]["id"]]
    assert data["evidence"][0]["image"]["thumb"].endswith("_w480.jpg")
    assert data["changes"][0]["target_id"] == src["id"] and data["changes"][0]["status"] == "edited"
    assert data["parties"][0]["mentions"] >= 0


def test_exclusions_carry_no_author(populated):
    project, *_ = populated
    _, data = _data(project)
    assert data["exclusions"] and all(set(x) <= {"id", "recorded_at", "url", "excerpt", "keywords_matched", "reason"}
                                      for x in data["exclusions"])


def test_write_is_atomic_and_idempotent(populated):
    project, *_ = populated
    _, first = _data(project)
    _, second = _data(project)
    first.pop("generated_at"), second.pop("generated_at")
    assert first == second
    assert not list((project.root / "output" / "site").glob("*.tmp"))


def test_empty_store_exports(project):
    result, data = _data(project)
    assert result["status"] == "ok" and data["sources"] == [] and data["stats"]["totals"]["sources"] == 0


def test_cli(populated, capsys):
    project, *_ = populated
    assert export_site.main(["--project", str(project.root)]) == 0
    assert json.loads(capsys.readouterr().out)["file"].endswith("data.json")


def test_recaptured_post_shows_newest_images_and_all_captures(project, make_png):
    from factories import ev, fb_source
    cfg = project.load_config()
    [src] = add_records(project, [fb_source([ev(make_png("a.png"))])], RUN, cfg)
    [chk] = add_records(project, [{"record_type": "recheck", "target_id": src["id"], "status": "active",
                                   "checked_at": "2026-10-02T10:00:00+07:00", "evidence": [ev(make_png("b.png"))]}],
                        RUN, cfg)
    _, data = _data(project)
    s = data["sources"][0]
    assert s["main_image"]["file"] == chk["evidence_paths"][0]
    assert [len(c["images"]) for c in s["captures"]] == [1, 1]
    assert s["captures"][1]["record_id"] == chk["id"]
