import json

import fb_search_logs
from add_record import add_records
from factories import fb_container

G = "427692059062534"


def _jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_feed_passes_and_search_tasks_become_logs(project):
    run = "RUN-2026-10-01-01"
    add_records(project, [fb_container()], run, project.load_config())
    rd = project.run_dir(run)
    (rd / "feeds").mkdir(parents=True)
    (rd / "search").mkdir()
    post = lambda n, at: {"pos": n, "permalink": f"https://www.facebook.com/groups/{G}/posts/{n}/", "seen_at": at}
    _jsonl(rd / "feeds" / f"group_{G}.jsonl", [post(1, "2026-10-01T09:00:00+07:00"), post(2, "2026-10-01T09:01:00+07:00"),
                                               {"pos": 3, "permalink": f"https://www.facebook.com/groups/{G}/#pos3",
                                                "seen_at": "2026-10-01T09:02:00+07:00"},
                                               post(4, "2026-10-01T10:00:30+07:00")])
    (rd / "feeds" / f"group_{G}.meta.json").write_text(json.dumps({
        "started_at": "2026-10-01T10:00:00+07:00", "ended_at": "2026-10-01T10:05:00+07:00", "reached_end": True,
        "posts_seen": 9, "passes": [{"started_at": "2026-10-01T09:00:00+07:00"}]}), encoding="utf-8")
    _jsonl(rd / "search" / "001_posts.jsonl", [post(2, "2026-10-01T11:00:00+07:00"), post(5, "2026-10-01T11:00:05+07:00")])
    (rd / "search" / "done.json").write_text(json.dumps({"001": {
        "kind": "search", "section": "posts", "query": "Roxana", "filters": {"year": 2021}, "file": "001_posts.jsonl",
        "started_at": "2026-10-01T11:00:00+07:00", "ended_at": "2026-10-01T11:02:00+07:00", "results_seen": 2,
        "reached_end": True}}), encoding="utf-8")
    first, second, search = fb_search_logs.build(project, run)
    assert (first["container_id"], first["results_new"], first["reached_end"]) == ("FB-G0001", 2, False)
    assert any("dừng giữa chừng" in i for i in first["issues"]) and any("1 bài không lấy được link" in i for i in first["issues"])
    assert (second["results_seen"], second["results_new"], second["reached_end"]) == (9, 1, True)
    assert (search["scope"], search["filters"], search["results_new"], search["results_duplicate"]) == ("global", {"year": 2021}, 1, 1)
    res = add_records(project, [first, second, search], run, project.load_config())
    assert [r["status"] for r in res] == ["added"] * 3
    assert [r["status"] for r in add_records(project, [first], run, project.load_config())] == ["duplicate"]
