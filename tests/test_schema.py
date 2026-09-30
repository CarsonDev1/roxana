from factories import ev, fb_comment, fb_container, fb_source
from schema import DESCRIPTIONS, ENUMS, LABELS, label, validate


def test_valid_scan_source_passes(project, make_png):
    assert validate(fb_source([ev(make_png())]), project.load_config()) == []


def test_scan_source_requires_evidence_and_snapshot(project):
    rec = fb_source([])
    rec.pop("snapshot_text")
    errors = validate(rec, project.load_config())
    assert any("ít nhất 1 ảnh" in e for e in errors)
    assert any("snapshot" in e for e in errors)


def test_legacy_source_exempt_from_evidence(project):
    rec = fb_source([], origin="legacy", tone=None, claim_type=None, importance_reason=None)
    rec.pop("snapshot_text")
    assert validate(rec, project.load_config()) == []


def test_missing_required_field_reported(project, make_png):
    rec = fb_source([ev(make_png())])
    del rec["author_name"]
    assert "Thiếu trường bắt buộc: author_name" in validate(rec, project.load_config())


def test_enum_and_config_violations(project, make_png):
    rec = fb_source([ev(make_png())], tone="rat_xau", topics=["ban_chui", "abc"],
                    keywords_matched=["khong_co"], entities_mentioned=["ai_do"])
    errors = validate(rec, project.load_config())
    assert any(e.startswith("tone=") for e in errors)
    assert any("abc" in e for e in errors)
    assert any("khong_co" in e for e in errors)
    assert any("ai_do" in e for e in errors)


def test_bad_evidence_item(project, make_png):
    rec = fb_source([{"file": str(make_png()), "kind": "toan_canh"}])
    errors = validate(rec, project.load_config())
    assert any("evidence[0]" in e and "kind" in e for e in errors)
    assert any("evidence[0]" in e and "shows" in e for e in errors)


def test_comment_rules(project):
    cfg = project.load_config()
    assert any("parent_comment_id" in e for e in validate(fb_comment("FB-P00001", "s.png", depth=2), cfg))
    errors = validate(fb_comment("FB-P00001", "s.png", importance="cao"), cfg)
    assert any("ảnh chụp riêng" in e for e in errors)
    assert any("importance_reason" in e for e in errors)
    assert any("scroll_refs" in e for e in validate(fb_comment("FB-P00001", "s.png", scroll_refs=[]), cfg))
    assert any("depth" in e for e in validate(fb_comment("FB-P00001", "s.png", depth=4), cfg))


def test_recheck_rules():
    edited = {"record_type": "recheck", "target_id": "FB-P00001", "checked_at": "2026-09-29T21:00:00+07:00",
              "status": "edited"}
    assert any("new_text" in e for e in validate(edited))
    bad = {"record_type": "recheck", "target_id": "FB-G0001", "checked_at": "2026-09-29T21:00:00+07:00",
           "status": "active", "updates": {"id": "hack"}}
    assert any("updates" in e for e in validate(bad))
    assert validate(dict(bad, updates={"joined": "yes"})) == []


def test_exclusion_must_not_name_author():
    rec = {"record_type": "exclusion", "url": "https://www.facebook.com/x", "excerpt": "a" * 101,
           "keywords_matched": ["lien"], "reason": "Trùng tên", "author_name": "Ai đó"}
    errors = validate(rec)
    assert any("100" in e for e in errors)
    assert any("tên người đăng" in e for e in errors)


def test_container_and_log_valid():
    assert validate(fb_container()) == []
    log = {"record_type": "search_log", "platform": "facebook", "scope": "global", "section": "posts",
           "query": "Roxana Plaza", "filters": {"year": 2021}, "started_at": "2026-09-29T20:00:00+07:00",
           "results_seen": 40, "results_new": 12, "reached_end": False, "issues": "Facebook chỉ trả 40 kết quả"}
    assert validate(log) == []


def test_unknown_record_type():
    assert validate({"record_type": "note"}) == ["record_type không hợp lệ: 'note'"]


def test_labels_and_descriptions_consistent():
    for name, values in ENUMS.items():
        if name != "record_type":
            assert set(LABELS[name]) == values
    for name, descriptions in DESCRIPTIONS.items():
        assert set(descriptions) == ENUMS[name]
    assert label("tone", "gay_gat") == "Gay gắt"
    assert label("tone", None) == ""
    assert label("tone", "la") == "la"


def test_recheck_may_correct_classification_of_source_with_reason(project):
    cfg = project.load_config()
    base = {"record_type": "recheck", "target_id": "WEB-P00003", "checked_at": "2026-09-29T21:00:00+07:00",
            "status": "active"}
    fix = dict(base, updates={"claim_type": "thong_tin", "importance": "trung_binh"}, notes="Bài chỉ thuật lại kết luận")
    assert validate(fix, cfg) == []
    assert any("notes" in e for e in validate(dict(fix, notes=None), cfg))
    assert any("claim_type" in e for e in validate(dict(fix, updates={"claim_type": "bịa"}), cfg))
    assert any("entities_mentioned" in e for e in validate(dict(fix, updates={"entities_mentioned": ["ai"]}), cfg))
    assert any("updates" in e for e in validate(dict(fix, updates={"text": "sửa nội dung"}), cfg))
    assert any("updates" in e for e in validate(dict(fix, target_id="FB-G0001"), cfg))  # nhóm: chỉ trường của nhóm


def test_recheck_may_extend_event_sources(project):
    cfg = project.load_config()
    base = {"record_type": "recheck", "target_id": "EVT-000012", "checked_at": "2026-09-29T21:00:00+07:00", "status": "active",
            "updates": {"related_ids": ["WEB-P00001", "WEB-P00002"]}, "notes": "Thêm bài mới cùng đưa tin"}
    assert validate(base, cfg) == []
    assert any("updates" in e for e in validate(dict(base, updates={"description": "sửa"}), cfg))
    assert any("notes" in e for e in validate(dict(base, notes=None), cfg))
