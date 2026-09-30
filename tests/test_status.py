import json
from datetime import datetime

import pytest

import status
from add_record import add_records
from common import TZ
from factories import ev, fb_container, fb_source
from status import add_tasks, init_progress, load_view, recheck_due, report, set_task, stats, summary


def _src(make_png, n, importance, captured, **kw):
    return fb_source([ev(make_png(f"s{n}.png"))], url=f"https://www.facebook.com/groups/1/posts/{n}",
                     importance=importance, captured_at=captured, **kw)


def test_recheck_due_policy(project, make_png):
    cfg = project.load_config()
    add_records(project, [_src(make_png, 1, "cao", "2026-10-10T12:00:00+07:00"),
                          _src(make_png, 2, "trung_binh", "2026-10-01T12:00:00+07:00"),
                          _src(make_png, 3, "thap", "2026-07-01T12:00:00+07:00"),
                          _src(make_png, 4, "cao", "2026-10-10T12:00:00+07:00")], "RUN-2026-10-10-01", cfg)
    legacy = fb_source([], origin="legacy", url="https://www.facebook.com/groups/1/posts/9",
                       tone=None, claim_type=None, importance_reason=None)
    legacy.pop("snapshot_text")
    add_records(project, [legacy], "LEGACY-IMPORT", cfg)
    add_records(project, [{"record_type": "recheck", "target_id": "FB-P00004", "status": "deleted",
                           "checked_at": "2026-10-10T13:00:00+07:00"}], "RUN-2026-10-10-01", cfg)
    add_records(project, [_src(make_png, 5, "cao", "2026-10-11T10:00:00+07:00")], "RUN-2026-10-11-01", cfg)
    due = recheck_due(load_view(project), cfg, "RUN-2026-10-11-01", now=datetime(2026, 10, 11, 12, 0, tzinfo=TZ))
    assert [d["id"] for d in due] == ["FB-P00001", "FB-P00005", "FB-P00003"]
    assert "file cũ" in due[1]["reason"]


def test_stats(project, make_png):
    cfg = project.load_config()
    add_records(project, [fb_container(), _src(make_png, 1, "cao", "2026-10-10T12:00:00+07:00")],
                "RUN-2026-10-10-01", cfg)
    s = stats(load_view(project))
    assert s["sources"] == 1 and s["containers_need_join"] == 1
    assert s["sources_by_platform"] == {"facebook": 1}


def test_progress_lifecycle(project):
    run = "RUN-2026-09-29-01"
    p = init_progress(project, run, "full")
    assert p["mode"] == "full" and p["tasks"] == []
    p = add_tasks(project, run, [
        {"kind": "search", "section": "posts", "query": "Roxana Plaza", "filters": {"year": 2021}},
        {"kind": "search", "section": "posts", "query": "Roxana Plaza", "filters": {"year": 2021}},
        {"kind": "container", "container_id": "FB-G0001"},
    ])
    assert [t["id"] for t in p["tasks"]] == ["T001", "T002"]
    assert all(t["status"] == "pending" for t in p["tasks"])
    set_task(project, run, "T001", "done", log_id="LOG-000001")
    p = init_progress(project, run, "update")  # không ghi đè
    assert p["mode"] == "full"
    assert p["tasks"][0]["status"] == "done" and p["tasks"][0]["log_id"] == "LOG-000001"
    assert summary(p) == {"total": 2, "done": 1, "pending": 1, "blocked": 0, "next": [p["tasks"][1]]}
    with pytest.raises(ValueError):
        set_task(project, run, "T999", "done")
    with pytest.raises(ValueError):
        set_task(project, run, "T001", "xong")


def test_report(project, make_png):
    cfg = project.load_config()
    run = "RUN-2026-10-11-01"
    init_progress(project, run, "update")
    add_tasks(project, run, [{"kind": "container", "container_id": "FB-G0001"}])
    set_task(project, run, "T001", "blocked", note="Facebook báo tạm thời bị chặn")
    add_records(project, [fb_container(), _src(make_png, 1, "cao", "2026-10-11T12:00:00+07:00"),
                          {"record_type": "search_log", "platform": "facebook", "scope": "global",
                           "section": "posts", "query": "Naviland", "started_at": "2026-10-11T12:00:00+07:00",
                           "results_seen": 40, "results_new": 1, "reached_end": False,
                           "issues": "Facebook chỉ trả 40 kết quả"}], run, cfg)
    add_records(project, [{"record_type": "recheck", "target_id": "FB-P00001", "status": "deleted",
                           "checked_at": "2026-10-11T13:00:00+07:00"}], run, cfg)
    path = report(project, load_view(project), cfg, run)
    assert path == project.run_dir(run) / "report.md"
    text = path.read_text(encoding="utf-8")
    for needle in ("FB-P00001", "ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ", "Facebook chỉ trả 40 kết quả", "Đã xoá",
                   "bị chặn", "tạm thời bị chặn"):
        assert needle in text


def test_cli(project, capsys, tmp_path):
    root = str(project.root)
    run = "RUN-2026-10-11-01"
    assert status.main(["--project", root, "stats"]) == 0
    assert json.loads(capsys.readouterr().out)["sources"] == 0
    assert status.main(["--project", root, "progress", "--run", run, "--init", "full"]) == 0
    capsys.readouterr()
    tasks = tmp_path / "tasks.json"
    tasks.write_text(json.dumps([{"kind": "search", "section": "posts", "query": "Roxana"}]), encoding="utf-8")
    assert status.main(["--project", root, "progress", "--run", run, "--add-tasks", str(tasks)]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 1
    assert status.main(["--project", root, "progress", "--run", run, "--set", "T001=done:LOG-000001"]) == 0
    assert json.loads(capsys.readouterr().out)["done"] == 1
    assert status.main(["--project", root, "recheck-due", "--run", run]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert status.main(["--project", root, "report", "--run", run]) == 0
    assert json.loads(capsys.readouterr().out)["file"].endswith("report.md")


def test_report_lists_issues_as_text(project):
    cfg = project.load_config()
    run = "RUN-2026-10-12-01"
    add_records(project, [{"record_type": "search_log", "platform": "facebook", "scope": "global",
                           "section": "posts", "query": "Roxana", "started_at": "2026-10-12T09:00:00+07:00",
                           "results_seen": 40, "results_new": 0, "reached_end": False,
                           "issues": ["Facebook chỉ trả 40 kết quả", "Yêu cầu đăng nhập lại"]}], run, cfg)
    text = report(project, load_view(project), cfg, run).read_text(encoding="utf-8")
    assert "Facebook chỉ trả 40 kết quả; Yêu cầu đăng nhập lại" in text
    assert "['" not in text
