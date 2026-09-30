"""Push the local store to its Supabase copy (one way: this machine → Supabase). Run after export_site.py.

python sync_supabase.py [--dry-run]

- records.jsonl → table `records` (new ids only; the store is append-only so existing rows never change)
- every evidence image / thumbnail referenced by the store or data.json → Storage bucket `evidence`, same relative
  path (uploaded again only when its SHA-256 changes)
- output/site/data.json → a new row in `site_snapshots` when it changed (the web reads the newest; last 10 are kept)

Credentials: <project>/.env.supabase (git-ignored) with SUPABASE_SECRET_KEY=... (Supabase → Project Settings → API keys →
secret key; never put it in web/ or commit it). SUPABASE_URL defaults to NEXT_PUBLIC_SUPABASE_URL in web/.env.local.
Tables/bucket: run supabase/schema.sql once in the Supabase SQL Editor. Progress: output/supabase_sync.json.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import Project, read_records, sha256_file, setup_stdout

FILE_RE = re.compile(r"^(screenshots|snapshots|output/thumbs)/[^\0]+$")
KEEP_SNAPSHOTS = 10


def _env(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


class Supabase:
    def __init__(self, url: str, key: str):
        self.url, self.key = url.rstrip("/"), key

    def request(self, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
        h = {"apikey": self.key, **(headers or {})}
        if self.key.startswith("eyJ"):  # khoá service_role kiểu cũ (JWT) cần cả Authorization
            h["Authorization"] = f"Bearer {self.key}"
        for attempt in range(4):
            req = urllib.request.Request(self.url + path, data=body, method=method, headers=h)
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw and "json" in resp.headers.get("Content-Type", "") else raw
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:500]
                if exc.code >= 500 and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"{method} {path.split('?')[0]} → HTTP {exc.code}: {detail}") from None
            except urllib.error.URLError as exc:
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(f"{method} {path.split('?')[0]} → {exc.reason}") from None


def _paths(obj, out: set[str]):
    if isinstance(obj, dict):
        for v in obj.values():
            _paths(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _paths(v, out)
    elif isinstance(obj, str) and FILE_RE.match(rel := obj.replace("\\", "/")) and ".." not in rel.split("/"):
        out.add(rel)


def main(argv=None) -> int:
    setup_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    project = Project()
    root = project.root
    env = {**_env(root / "web" / ".env.local"), **_env(root / ".env.supabase")}
    url = env.get("SUPABASE_URL") or env.get("NEXT_PUBLIC_SUPABASE_URL")
    key = env.get("SUPABASE_SECRET_KEY")
    if not url or (not key and not args.dry_run):
        print(json.dumps({"status": "missing_credentials",
                          "hint": "Tạo file .env.supabase ở thư mục dự án với dòng SUPABASE_SECRET_KEY=<secret key>"},
                         ensure_ascii=False))
        return 2
    sb = Supabase(url, key or "")
    state_f = root / "output" / "supabase_sync.json"
    state = json.loads(state_f.read_text(encoding="utf-8")) if state_f.exists() else {}
    synced_ids, synced_files = set(state.get("records", [])), dict(state.get("files", {}))

    records, _ = read_records(project.records_path)
    site_f = root / "output" / "site" / "data.json"
    site = json.loads(site_f.read_text(encoding="utf-8")) if site_f.exists() else None
    files: set[str] = set()
    _paths(records, files)
    if site:
        _paths(site, files)

    new_recs = [r for r in records if r.get("id") and r["id"] not in synced_ids]
    todo_files = []
    missing = []
    for rel in sorted(files):
        p = root / rel
        if not p.is_file():
            missing.append(rel)
            continue
        digest = sha256_file(p)
        if synced_files.get(rel) != digest:
            todo_files.append((rel, p, digest))
    snap_needed = bool(site) and state.get("snapshot_generated_at") != site.get("generated_at")
    plan = {"records_new": len(new_recs), "files_new": len(todo_files), "files_missing_locally": missing[:10],
            "files_bytes": sum(p.stat().st_size for _, p, _ in todo_files), "snapshot": snap_needed}
    if args.dry_run:
        print(json.dumps({"status": "dry_run", **plan}, ensure_ascii=False, indent=1))
        return 0

    def save():
        state.update(records=sorted(synced_ids), files=synced_files)
        state_f.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    for i in range(0, len(new_recs), 500):
        chunk = new_recs[i:i + 500]
        rows = [{"id": r["id"], "record_type": r.get("record_type"), "recorded_at": r.get("recorded_at"), "data": r}
                for r in chunk]
        sb.request("POST", "/rest/v1/records?on_conflict=id", json.dumps(rows, ensure_ascii=False).encode("utf-8"),
                   {"Content-Type": "application/json", "Prefer": "resolution=ignore-duplicates,return=minimal"})
        synced_ids.update(r["id"] for r in chunk)
        save()
    for n, (rel, p, digest) in enumerate(todo_files, 1):
        key_path = "/".join(urllib.parse.quote(s) for s in rel.split("/"))
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        sb.request("POST", f"/storage/v1/object/evidence/{key_path}", p.read_bytes(),
                   {"Content-Type": ctype, "x-upsert": "true", "Cache-Control": "max-age=31536000"})
        synced_files[rel] = digest
        if n % 20 == 0:
            save()
            print(json.dumps({"files_uploaded": n, "of": len(todo_files)}), flush=True)
    save()
    if snap_needed:
        row = {"generated_at": site["generated_at"], "schema_version": site.get("schema_version", 1), "data": site}
        sb.request("POST", "/rest/v1/site_snapshots", json.dumps(row, ensure_ascii=False).encode("utf-8"),
                   {"Content-Type": "application/json", "Prefer": "return=minimal"})
        state["snapshot_generated_at"] = site["generated_at"]
        save()
        ids = sb.request("GET", f"/rest/v1/site_snapshots?select=id&order=id.desc&offset={KEEP_SNAPSHOTS}&limit=1")
        if ids:  # chỉ giữ vài bản gần nhất (bản dựng ra từ kho, không phải dữ liệu gốc)
            sb.request("DELETE", f"/rest/v1/site_snapshots?id=lte.{ids[0]['id']}", headers={"Prefer": "return=minimal"})
    print(json.dumps({"status": "ok", **plan}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
