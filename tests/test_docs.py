import re
from pathlib import Path

from schema import ENUMS

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "mention-monitor"


def _read(rel):
    return (SKILL / rel).read_text(encoding="utf-8")


def test_skill_frontmatter():
    m = re.match(r"^---\r?\nname: mention-monitor\r?\ndescription: (.+?)\r?\n---\r?\n", _read("SKILL.md"), re.S)
    assert m and len(m.group(1)) < 1024


def test_referenced_files_exist():
    text = _read("SKILL.md")
    for ref in re.findall(r"references/[\w.-]+\.md", text):
        assert (SKILL / ref).is_file(), ref
    for script in re.findall(r"scripts/(\w+\.py)", text):
        assert (SKILL / "scripts" / script).is_file(), script


def test_classification_lists_every_enum_value():
    text = _read("references/classification.md")
    for name in ("tone", "claim_type", "topics", "importance"):
        for value in ENUMS[name]:
            assert f"`{value}`" in text, (name, value)


def test_schema_doc_lists_enums():
    text = _read("references/schema.md")
    for name in ("content_type", "url_kind", "author_kind", "posted_at_precision", "section", "recheck_status",
                 "evidence_kind", "reliability", "joined", "privacy", "scan_mode"):
        for value in ENUMS[name]:
            assert f"`{value}`" in text, (name, value)


def test_facebook_doc_has_key_rules():
    text = _read("references/facebook.md")
    for needle in ("Tất cả bình luận", "tạm thời bị chặn", "CAPTCHA", "save_to_disk", "evidence_paths",
                   "search_log", "exclusion", "recheck"):
        assert needle in text, needle


def test_docs_do_not_hardcode_project_path():
    for rel in ("SKILL.md", "references/schema.md", "references/classification.md", "references/facebook.md"):
        assert "D:\Roxana" not in _read(rel), rel
