from view import build_view, needs_join


def S(id_, **kw):
    return {"record_type": "source", "id": id_, "platform": "facebook", "origin": "scan", "importance": "trung_binh",
            "metrics": {"reactions": 1}, "evidence": [{"file": f"screenshots/{id_}.png", "kind": "post"}], **kw}


def C(id_, sid, parent=None, **kw):
    return {"record_type": "comment", "id": id_, "source_id": sid, "parent_comment_id": parent, "reactions": 0, **kw}


def K(id_, target, status="active", at="2026-10-01T00:00:00+07:00", **kw):
    return {"record_type": "recheck", "id": id_, "target_id": target, "status": status, "checked_at": at, **kw}


def test_recheck_merge_and_changes():
    v = build_view([
        S("FB-P00001"),
        K("CHK-000001", "FB-P00001", metrics={"reactions": 1}),
        K("CHK-000002", "FB-P00001", "edited", at="2026-10-02T00:00:00+07:00", new_text="Đã sửa",
          metrics={"reactions": 5}, evidence=[{"file": "screenshots/CHK-000002_post_01.png", "kind": "post"}]),
    ])
    s = v.sources[0]
    assert s["status"] == "edited" and s["current_text"] == "Đã sửa"
    assert s["current_metrics"]["reactions"] == 5
    assert s["last_checked_at"] == "2026-10-02T00:00:00+07:00"
    assert len(s["all_evidence"]) == 2
    assert [c["id"] for c in v.changes] == ["CHK-000002"]
    assert v.changes[0]["_metrics_grew"] is True


def test_rechecks_applied_in_time_order_not_file_order():
    v = build_view([S("FB-P00001"),
                    K("CHK-000002", "FB-P00001", "deleted", at="2026-10-05T00:00:00+07:00"),
                    K("CHK-000001", "FB-P00001", "active", at="2026-10-01T00:00:00+07:00")])
    assert v.sources[0]["status"] == "deleted"


def test_superseded_legacy_hidden():
    v = build_view([S("FB-P00001", origin="legacy"), S("FB-P00002", supersedes="FB-P00001")])
    assert [s["id"] for s in v.sources] == ["FB-P00002"]
    assert v.superseded == {"FB-P00001"}


def test_container_updates_and_needs_join():
    ctr = {"record_type": "container", "id": "FB-G0001", "privacy": "private", "joined": "no", "name": "Nhóm"}
    before = build_view([ctr])
    assert needs_join(before.containers[0])
    v = build_view([ctr, K("CHK-000001", "FB-G0001",
                           updates={"joined": "yes", "last_scanned_at": "2026-10-01T00:00:00+07:00"})])
    assert v.containers[0]["joined"] == "yes" and not needs_join(v.containers[0])
    assert v.changes[0]["target_id"] == "FB-G0001"


def test_comment_tree_order_and_counts():
    v = build_view([S("FB-P00001"), S("FB-P00002"),
                    C("FB-C000001", "FB-P00001"), C("FB-C000002", "FB-P00002"),
                    C("FB-C000003", "FB-P00001", "FB-C000001"), C("FB-C000004", "FB-P00001")])
    assert [c["id"] for c in v.comments] == ["FB-C000001", "FB-C000003", "FB-C000004", "FB-C000002"]
    assert {s["id"]: s["comments_collected"] for s in v.sources} == {"FB-P00001": 3, "FB-P00002": 1}


def test_recheck_for_unknown_target_warns():
    v = build_view([K("CHK-000001", "FB-P09999")], warnings=["cũ"])
    assert v.warnings[0] == "cũ" and "FB-P09999" in v.warnings[1]


def test_events_sorted_by_sort_key():
    v = build_view([
        {"record_type": "event", "id": "EVT-0002", "date": None, "sort_key": "2021-01-22"},
        {"record_type": "event", "id": "EVT-0001", "date": "2017", "sort_key": "2017"},
        {"record_type": "event", "id": "EVT-0003", "date": "2026-08-22"},
    ])
    assert [e["id"] for e in v.events] == ["EVT-0001", "EVT-0002", "EVT-0003"]


def test_reclassification_applies_and_is_logged():
    v = build_view([S("WEB-P00001", claim_type="van_ban"),
                    K("CHK-000001", "WEB-P00001", updates={"claim_type": "thong_tin"}, notes="chỉ thuật lại")])
    assert v.sources[0]["claim_type"] == "thong_tin"
    assert v.changes[0]["target_id"] == "WEB-P00001"


def test_event_sources_extended_by_recheck():
    ev = {"record_type": "event", "id": "EVT-0001", "date": "2021-11-04", "description": "Phạt", "related_ids": ["WEB-P00001"]}
    v = build_view([ev, K("CHK-000001", "EVT-0001", updates={"related_ids": ["WEB-P00001", "WEB-P00009"]}, notes="thêm")])
    assert v.events[0]["related_ids"] == ["WEB-P00001", "WEB-P00009"]
