"""Google Trends — mức quan tâm tìm kiếm trên Google theo từng nhóm từ khoá (không phải từng bài).

python trends.py [--project DIR] [--from 2017-01-01] [--geo VN]

Mỗi nhóm trong config.json → keyword_groups: lấy cụm đầu tiên (không phải hashtag) làm từ khoá, hỏi Google Trends
chuỗi theo tháng từ --from tới nay. Ghi <project>/data/trends.json; export_site.py đưa vào data.json cho trang Tổng quan.
Chỉ số Trends là TƯƠNG ĐỐI (0–100, 100 = tháng được tìm nhiều nhất của CHÍNH nhóm đó), không phải số lượt tìm tuyệt
đối, và không so sánh được giữa các nhóm. Google trả 429/chặn → dừng, ghi lỗi, không vượt qua.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from common import TZ, Project, setup_stdout

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0 Safari/537.36"
BASE = "https://trends.google.com/trends/"


def _strip_prefix(body: str) -> dict:
    return json.loads(body[body.index("{"):])  # Google đặt ")]}'" trước JSON


def parse_timeline(body: str) -> list[dict]:
    """Phản hồi widgetdata/multiline → [{"date": "2024-05", "value": 37, "partial": False}, …]."""
    out = []
    for p in _strip_prefix(body)["default"]["timelineData"]:
        date = datetime.fromtimestamp(int(p["time"]), timezone.utc).astimezone(TZ).strftime("%Y-%m")
        out.append({"date": date, "value": int((p.get("value") or [0])[0]), "partial": bool(p.get("isPartial"))})
    return out


def summarize(points: list[dict]) -> dict:
    full = [p for p in points if not p["partial"]] or points
    peak = max(full, key=lambda p: p["value"], default=None)
    last12 = [p["value"] for p in full[-12:]]
    return {"peak_month": peak["date"] if peak and peak["value"] else None, "peak_value": peak["value"] if peak else None,
            "avg_last_12_months": round(sum(last12) / len(last12), 1) if last12 else None,
            "last_month": full[-1]["date"] if full else None, "last_value": full[-1]["value"] if full else None}


class Trends:
    def __init__(self, geo: str = "VN"):
        self.geo = geo
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener.addheaders = [("User-Agent", UA), ("Accept-Language", "vi-VN,vi;q=0.9")]
        self.opener.open(f"{BASE}?geo={geo}", timeout=40).read()  # lấy cookie NID

    def _get(self, endpoint: str, params: dict) -> str:
        with self.opener.open(BASE + endpoint + "?" + urllib.parse.urlencode(params), timeout=40) as r:
            return r.read().decode("utf-8", "replace")

    def timeline(self, keyword: str, start: str, end: str) -> list[dict]:
        req = {"comparisonItem": [{"keyword": keyword, "geo": self.geo, "time": f"{start} {end}"}], "category": 0, "property": ""}
        widgets = _strip_prefix(self._get("api/explore", {"hl": "vi", "tz": "-420", "req": json.dumps(req)}))["widgets"]
        w = next(x for x in widgets if x.get("id") == "TIMESERIES")
        body = self._get("api/widgetdata/multiline",
                         {"hl": "vi", "tz": "-420", "req": json.dumps(w["request"]), "token": w["token"]})
        return parse_timeline(body)


def keyword_of(group: dict) -> str | None:
    return next((t for t in group.get("terms", []) if not t.startswith("#")), None)


def run(project: Project, start: str, geo: str) -> dict:
    config = project.load_config()
    now = datetime.now(TZ)
    end = now.strftime("%Y-%m-%d")
    out = {"source": "Google Trends", "geo": geo, "from": start, "to": end, "fetched_at": now.isoformat(timespec="seconds"),
           "note": "Chỉ số tương đối 0–100 theo từng nhóm (100 = tháng được tìm nhiều nhất của chính nhóm đó); "
                   "không phải số lượt tìm tuyệt đối, không so sánh được giữa các nhóm.",
           "groups": []}
    client = Trends(geo)
    for g in config["keyword_groups"]:
        kw = keyword_of(g)
        entry = {"group": g["id"], "label": g["label"], "keyword": kw, "points": [], "error": None}
        if kw:
            try:
                entry["points"] = client.timeline(kw, start, end)
                entry.update(summarize(entry["points"]))
            except urllib.error.HTTPError as exc:
                entry["error"] = f"HTTP {exc.code}"
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
        out["groups"].append(entry)
        print(json.dumps({k: entry.get(k) for k in ("group", "keyword", "peak_month", "last_value", "error")}, ensure_ascii=False), flush=True)
        if entry["error"] and "429" in entry["error"]:  # bị giới hạn tốc độ → dừng, không vượt qua
            break
        time.sleep(random.uniform(3, 6))
    return out


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--from", dest="start", default="2017-01-01")
    ap.add_argument("--geo", default="VN")
    args = ap.parse_args(argv)
    project = Project(args.project) if args.project else Project()
    result = run(project, args.start, args.geo)
    path = project.root / "data" / "trends.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    errors = [g["group"] for g in result["groups"] if g["error"]]
    print(json.dumps({"status": "ok" if not errors else "partial", "file": str(path), "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
