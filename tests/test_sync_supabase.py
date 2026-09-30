import sync_supabase


def test_collects_only_evidence_paths():
    out = set()
    sync_supabase._paths({"evidence": [{"file": chr(92).join(["screenshots", "web", "a.png"]), "thumb": "output/thumbs/a_w240.jpg"}],
                          "config": "config.json", "x": ["data/records.jsonl", "snapshots/p.txt", "../screenshots/b.png", "screenshots/../config.json"]}, out)
    assert out == {"screenshots/web/a.png", "output/thumbs/a_w240.jpg", "snapshots/p.txt"}


def test_env_file_parsing(tmp_path):
    f = tmp_path / ".env.supabase"
    f.write_text("# khoá\nSUPABASE_SECRET_KEY = 'sb_secret_x'\nNEXT_PUBLIC_SUPABASE_URL=https://p.supabase.co\n", encoding="utf-8")
    assert sync_supabase._env(f) == {"SUPABASE_SECRET_KEY": "sb_secret_x", "NEXT_PUBLIC_SUPABASE_URL": "https://p.supabase.co"}
    assert sync_supabase._env(tmp_path / "missing") == {}
