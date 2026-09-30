"""Run the search matrix (plan_search.py output) in its own Chrome window, one task after another.

python run_search.py <tasks.json> <out_dir> [--only posts,groups,...]

posts / videos / photos / hashtag → collect_feed (one jsonl per task: every result with permalink, time, snippet)
groups / pages → entity list (name, url, snippet) per task
<out_dir>/done.json records finished task indexes (resume); runs/STOP from any lane stops this one too.
"""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import collect_feed  # noqa: E402
from collect_feed import blocked  # noqa: E402
from window import own_window, request_stop, stop_requested  # noqa: E402

ENTITIES = r"""
(kind) => {
  const re = kind === 'groups' ? /facebook\.com\/groups\/([^/?#]+)\/?(?:\?|$)/ : /facebook\.com\/(?!groups\/|search\/|hashtag\/|watch|photo|reel|events|marketplace|gaming)([^/?#]+)\/?(?:\?|$)|profile\.php\?id=\d+/;
  const seen = new Map();
  for (const a of document.querySelectorAll('[role="main"] a[href]')) {
    const m = a.href.match(re);
    const name = a.innerText.trim();
    if (!m || !name || name.length > 120) continue;
    const url = a.href.split('?')[0].replace(/\/$/, '') + '/';
    if (seen.has(url)) continue;
    const card = a.closest('[role="article"]') || a.parentElement?.parentElement?.parentElement?.parentElement;
    seen.set(url, {name, url, snippet: card ? card.innerText.split('\n').filter(l => l.trim()).slice(0, 8).join(' · ').slice(0, 600) : null});
  }
  return [...seen.values()];
}
"""


def entity_task(b, task, out: Path) -> dict:
    p, close = own_window(b)
    try:
        p.goto(task["url"], wait_until="domcontentloaded", timeout=60000)
        p.wait_for_timeout(5000)
        if (why := blocked(p)):
            request_stop(f"run_search {task['url']}: {why}")
            return {"status": "blocked", "reason": why}
        found, stall, last = {}, 0, 0
        for _ in range(60):
            for e in p.evaluate(ENTITIES, task["section"]):
                found.setdefault(e["url"], e)
            p.mouse.wheel(0, random.randint(1500, 2200))
            p.wait_for_timeout(random.randint(2000, 3500))
            if len(found) == last:
                stall += 1
                if stall >= 4:
                    break
            else:
                stall, last = 0, len(found)
            if stop_requested():
                break
        end = p.evaluate("/Hết kết quả|End of results|Không tìm thấy kết quả|We didn't find/i.test(document.body.innerText)")
        out.write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in found.values()) + ("\n" if found else ""),
                       encoding="utf-8")
        return {"status": "ok", "results_seen": len(found), "reached_end": bool(end or stall >= 4)}
    finally:
        close()


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("tasks")
    ap.add_argument("out")
    ap.add_argument("--only")
    args = ap.parse_args(argv)
    tasks = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    done_file = out / "done.json"
    done = json.loads(done_file.read_text(encoding="utf-8")) if done_file.exists() else {}
    only = set(args.only.split(",")) if args.only else None
    for i, task in enumerate(tasks):
        key = f"{i:04d}"
        if key in done or (only and task["section"] not in only):
            continue
        if stop_requested():
            print(json.dumps({"status": "stopped"}, ensure_ascii=False)); return 3
        started = time.strftime("%Y-%m-%dT%H:%M:%S+07:00")
        slug = re.sub(r"\W+", "_", f"{task['section']}_{task['query']}_{json.dumps(task.get('filters') or {})}")[:80]
        target = out / f"{key}_{slug}.jsonl"
        if task["section"] in ("groups", "pages"):
            with sync_playwright() as pw:
                res = entity_task(pw.chromium.connect_over_cdp("http://127.0.0.1:9222"), task, target)
        else:
            argv2 = [task["url"], str(target), "--own-window", "--max", "400"]
            if task["section"] in ("videos", "photos", "hashtag"):
                argv2.append("--media-fallback")
            rc = collect_feed.main(argv2)
            meta_f = target.with_suffix(".meta.json")
            meta = json.loads(meta_f.read_text(encoding="utf-8")) if meta_f.exists() else {}
            res = {"status": "blocked" if rc == 3 else "ok", "results_seen": meta.get("posts_seen", 0),
                   "reached_end": meta.get("reached_end", False)}
        done[key] = {**task, **res, "started_at": started, "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                     "file": target.name}
        if res["status"] == "blocked":
            done.pop(key)
            done_file.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
            print(json.dumps({"status": "blocked", "task": key}, ensure_ascii=False)); return 3
        done_file.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"task": key, "section": task["section"], "query": task["query"],
                          "filters": task.get("filters"), **res}, ensure_ascii=False), flush=True)
        time.sleep(random.uniform(6, 14))
    print(json.dumps({"status": "ok", "done": len(done), "of": len(tasks)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
