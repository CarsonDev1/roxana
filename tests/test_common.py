import hashlib
import unicodedata

import pytest

from common import (DEFAULT_PROJECT, IdAllocator, append_records, dedupe_key, fold, match_keywords,
                    normalize_url, read_records, sha256_file, strip_accents)


def test_default_project_is_repo_root():
    assert (DEFAULT_PROJECT / ".claude" / "skills" / "mention-monitor" / "scripts" / "common.py").is_file()


@pytest.mark.parametrize("raw", [
    "https://www.facebook.com/groups/427692059062534/posts/1597546225410439/",
    "https://m.facebook.com/groups/427692059062534/posts/1597546225410439",
    "http://mbasic.facebook.com/groups/427692059062534/posts/1597546225410439/?__cft__[0]=AZX&__tn__=%2CO%2CP-R",
    "https://web.facebook.com/groups/427692059062534/posts/1597546225410439/?mibextid=abc#top",
    "facebook.com/groups/427692059062534/posts/1597546225410439/",
])
def test_normalize_facebook_post_variants(raw):
    assert normalize_url(raw) == "https://www.facebook.com/groups/427692059062534/posts/1597546225410439"


def test_normalize_keeps_identity_params_sorted():
    raw = ("https://www.facebook.com/photo/?set=gm.1597546225410439&fbid=961416423641269"
           "&idorvanity=427692059062534&__tn__=x")
    assert normalize_url(raw) == "https://www.facebook.com/photo?fbid=961416423641269&set=gm.1597546225410439"


def test_normalize_non_facebook_drops_tracking_only():
    raw = "https://cafef.vn/ket-luan.chn?utm_source=fb&fbclid=123&page=2"
    assert normalize_url(raw) == "https://cafef.vn/ket-luan.chn?page=2"


def test_normalize_empty():
    assert normalize_url("") == ""
    assert normalize_url(None) == ""


def test_fold_is_accent_case_space_and_form_insensitive():
    nfd = unicodedata.normalize("NFD", "Tường Phong")
    assert fold(nfd) == fold("TƯỜNG   PHONG") == "tuong phong"
    assert strip_accents("Đỗ Quý Phương Uyên") == "Do Quy Phuong Uyen"


def test_match_keywords_basic(project):
    matched, lacking = match_keywords("CĐT Tuong Phong vẫn chưa giao nhà Roxana", project.load_config())
    assert matched == ["roxana", "tuongphong"]
    assert lacking == []


def test_match_keywords_requires_context(project):
    cfg = project.load_config()
    matched, lacking = match_keywords("Chúc mừng sinh nhật chị Phạm Ngọc Liên!", cfg)
    assert matched == [] and lacking == ["lien"]
    matched, _ = match_keywords("Bà Phạm Thị Ngọc Liên", cfg, context_text="Nhóm ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ")
    assert matched == ["lien"]


def test_match_keywords_nfd_input(project):
    text = unicodedata.normalize("NFD", "Dự án Roxana Plaza của Tường Phong")
    assert match_keywords(text, project.load_config())[0] == ["roxana", "tuongphong"]


def test_id_allocator_continues_per_prefix():
    alloc = IdAllocator([{"id": "FB-P00007"}, {"id": "FB-C000002"}, {"id": "LOG-000010"}, {"id": "WEB-P00001"}])
    assert alloc.next("source", "facebook") == "FB-P00008"
    assert alloc.next("source", "facebook") == "FB-P00009"
    assert alloc.next("comment", "facebook") == "FB-C000003"
    assert alloc.next("container", "facebook") == "FB-G0001"
    assert alloc.next("search_log") == "LOG-000011"
    assert alloc.next("event") == "EVT-0001"
    assert alloc.next("source", "web") == "WEB-P00002"


def test_append_then_read_roundtrip_utf8(tmp_path):
    path = tmp_path / "data" / "records.jsonl"
    append_records(path, [{"id": "A", "text": "Hành trình đòi nhà =)))"}])
    append_records(path, [{"id": "B"}])
    records, warnings = read_records(path)
    assert [r["id"] for r in records] == ["A", "B"]
    assert records[0]["text"] == "Hành trình đòi nhà =)))"
    assert warnings == []


def test_read_skips_broken_line_and_append_recovers(tmp_path):
    path = tmp_path / "records.jsonl"
    path.write_text('{"id": "A"}\n{"id": "B", "te', encoding="utf-8")  # mất điện giữa lúc ghi
    records, warnings = read_records(path)
    assert [r["id"] for r in records] == ["A"] and len(warnings) == 1
    append_records(path, [{"id": "C"}])
    records, warnings = read_records(path)
    assert [r["id"] for r in records] == ["A", "C"] and len(warnings) == 1


def test_append_never_rewrites_existing_bytes(tmp_path):
    path = tmp_path / "records.jsonl"
    append_records(path, [{"id": "A"}])
    before = path.read_bytes()
    append_records(path, [{"id": "B"}])
    assert path.read_bytes().startswith(before)


def test_sha256_file_matches_hashlib(tmp_path):
    path = tmp_path / "x.bin"
    path.write_bytes(b"roxana" * 1000)
    assert sha256_file(path) == hashlib.sha256(b"roxana" * 1000).hexdigest()


def test_dedupe_key_source_permalink_uses_normalized_url():
    a = {"record_type": "source", "url_kind": "permalink", "url": "https://m.facebook.com/groups/1/posts/2/?__tn__=x"}
    b = {"record_type": "source", "url_kind": "permalink", "url": "https://www.facebook.com/groups/1/posts/2"}
    assert dedupe_key(a) == dedupe_key(b)


def test_dedupe_key_source_without_permalink_uses_content():
    base = {"record_type": "source", "url_kind": "container_only", "url": "https://www.facebook.com/groups/1/",
            "container_id": "FB-G0001", "author_name": "Lê Trọng Chiến"}
    a = dict(base, text="Nhóm đang lên kế hoạch  tố cáo")
    b = dict(base, text=unicodedata.normalize("NFD", "Nhóm đang lên kế hoạch tố cáo"))
    c = dict(base, text="Bài khác hẳn")
    assert dedupe_key(a) == dedupe_key(b) != dedupe_key(c)


def test_dedupe_key_comment_ignores_relative_time():
    a = {"record_type": "comment", "source_id": "FB-P00001", "author_name": "X", "text": "Trả nhà đi",
         "posted_at_raw": "2 giờ"}
    assert dedupe_key(a) == dedupe_key(dict(a, posted_at_raw="3 ngày"))
    assert dedupe_key(dict(a, fb_comment_id="123")) == "fbc:123"


def test_dedupe_key_none_for_rechecks():
    assert dedupe_key({"record_type": "recheck"}) is None


def test_project_resolve_and_rel(project):
    path = project.resolve("screenshots/facebook/x.png")
    assert path == project.root / "screenshots" / "facebook" / "x.png"
    assert project.rel(path) == "screenshots/facebook/x.png"
    assert project.resolve(str(path)) == path


WEAK_CFG = {
    "keyword_groups": [
        {"id": "roxana", "label": "Roxana Plaza", "terms": ["Roxana Plaza"], "weak_terms": ["Roxana"]},
        {"id": "tuongphong", "label": "CĐT Tường Phong", "terms": ["CĐT Tường Phong"], "weak_terms": ["Tường Phong"]},
        {"id": "naviland", "label": "Naviland", "terms": ["Naviland"]},
    ],
    "context_terms": ["Roxana", "Tường Phong", "Naviland", "Thuận An", "căn hộ"],
}


def test_accented_term_does_not_match_other_accents():
    # "tường phòng" (bức tường của căn phòng) không phải "Tường Phong"
    assert match_keywords("Vết nứt trên tường phòng khách ở Naviland", WEAK_CFG)[0] == ["naviland"]
    # viết không dấu vẫn khớp; chữ có dấu đúng như term cũng khớp
    assert match_keywords("CĐT Tuong Phong lua dao", WEAK_CFG)[0] == ["tuongphong"]
    assert match_keywords("cdt tuong phong", WEAK_CFG)[0] == ["tuongphong"]


def test_weak_term_needs_context():
    matched, lacking = match_keywords("BTV Roxana Vancea dẫn bản tin", WEAK_CFG)
    assert matched == [] and lacking == ["roxana"]
    matched, lacking = match_keywords("TS Bùi Tường Phong phát biểu", WEAK_CFG)
    assert matched == [] and lacking == ["tuongphong"]
    # từ yếu của nhóm này không tự làm ngữ cảnh cho chính nó, nhưng làm ngữ cảnh cho nhóm khác được
    assert match_keywords("Roxana của Tường Phong", WEAK_CFG)[0] == ["roxana", "tuongphong"]
    assert match_keywords("Chủ căn hộ Roxana", WEAK_CFG)[0] == ["roxana"]
    assert match_keywords("Roxana", WEAK_CFG, context_text="Nhóm cư dân Thuận An")[0] == ["roxana"]


def test_terms_match_whole_words():
    assert match_keywords("Naviland", WEAK_CFG)[0] == ["naviland"]
    assert match_keywords("Navilandia", WEAK_CFG)[0] == []
    assert match_keywords("#Naviland.", WEAK_CFG)[0] == ["naviland"]


def test_search_log_and_exclusion_dedupe_keys():
    log = {"record_type": "search_log", "platform": "web", "section": "news", "query": "Roxana Plaza",
           "started_at": "2026-09-30T11:49:06+07:00"}
    assert dedupe_key(log) == dedupe_key(dict(log)) != dedupe_key(dict(log, started_at="2026-09-30T11:50:00+07:00"))
    assert dedupe_key(dict(log, filters={"year": 2021})) != dedupe_key(log)
    exc = {"record_type": "exclusion", "url": "https://Example.com/a?utm_source=x"}
    assert dedupe_key(exc) == dedupe_key({"record_type": "exclusion", "url": "https://example.com/a"})


def test_person_names_need_case_context_not_generic_real_estate_words():
    cfg = {"keyword_groups": [{"id": "lien", "label": "Bà Liên", "terms": ["Phạm Ngọc Liên"], "requires_context": True},
                              {"id": "naviland", "label": "Naviland", "terms": ["Naviland"]}],
           "context_terms": ["căn hộ", "chủ đầu tư", "Naviland"], "case_context_terms": ["Naviland", "Roxana"]}
    assert match_keywords("Ông Phạm Ngọc Liên, Giám đốc Văn phòng đăng ký đất đai, nói về sổ hồng căn hộ", cfg) == ([], ["lien"])
    assert match_keywords("Bà Phạm Ngọc Liên, TGĐ Naviland", cfg)[0] == ["lien", "naviland"]
    assert match_keywords("Bà Phạm Ngọc Liên phát biểu", cfg, context_text="Nhóm cư dân Roxana")[0] == ["lien"]


def test_part_of_own_name_is_not_context():
    cfg = {"keyword_groups": [{"id": "lien", "label": "Bà Liên", "terms": ["Phạm Thị Ngọc Liên"], "requires_context": True}],
           "context_terms": ["Ngọc Liên"], "case_context_terms": ["Ngọc Liên", "Roxana"]}
    assert match_keywords("Thơ Phạm Thị Ngọc Liên — Mùa thu", cfg) == ([], ["lien"])
    assert match_keywords("Bà Phạm Thị Ngọc Liên và Roxana", cfg)[0] == ["lien"]
