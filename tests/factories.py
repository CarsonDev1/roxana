"""Record builders for tests. Values mirror real Roxana Plaza posts from the legacy file."""


def ev(path, kind="post", shows="Thân bài"):
    return {"file": str(path), "kind": kind, "shows": shows}


def fb_source(evidence=None, **over):
    rec = {
        "record_type": "source", "platform": "facebook", "content_type": "post",
        "url": "https://www.facebook.com/groups/427692059062534/posts/1597546225410439/",
        "url_kind": "permalink", "container_name": "ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ",
        "author_name": "Quyết Chiến Roxana", "author_url": "https://www.facebook.com/100093187612816",
        "author_kind": "person", "posted_at_raw": "22 tháng 8, 2026 lúc 09:15",
        "posted_at": "2026-08-22T09:15:00+07:00", "posted_at_precision": "exact",
        "text": "Hôm qua đã tổ chức cuộc họp giữa cư dân Roxana Plaza và cơ quan nhà nước.",
        "attachments": [{"kind": "image", "description": "Giấy mời của Thanh tra TP.HCM",
                         "transcribed_text": "GIẤY MỜI ... 8h00 ngày 22/8/2026"}],
        "metrics": {"reactions": 7, "comments": 2, "shares": 0, "views": None,
                    "counted_at": "2026-09-29T21:00:00+07:00"},
        "keywords_matched": ["roxana"], "entities_mentioned": ["lien"], "topics": ["doi_thoai"],
        "tone": "tieu_cuc", "claim_type": "van_ban", "importance": "cao",
        "importance_reason": "Kèm Giấy mời của Thanh tra TP.HCM",
        "evidence": evidence if evidence is not None else [],
        "snapshot_text": "Quyết Chiến Roxana · 22 tháng 8 lúc 09:15 · Hôm qua đã tổ chức cuộc họp...",
        "captured_at": "2026-09-29T21:00:00+07:00",
    }
    rec.update(over)
    return rec


def fb_comment(source_id, scroll_file, position=1, **over):
    rec = {
        "record_type": "comment", "source_id": source_id, "depth": 1,
        "author_name": "Huynh Bich Diem", "author_url": "https://www.facebook.com/100009329476350",
        "author_kind": "person", "posted_at_raw": "3 ngày", "posted_at": "2026-09-26T21:00:00+07:00",
        "posted_at_precision": "relative_estimate", "text": "Trả nhà cho dân đi =)))",
        "reactions": 3, "reply_count": 0, "keywords_matched": [], "entities_mentioned": [], "topics": [],
        "tone": "tieu_cuc", "claim_type": "y_kien", "importance": "thap",
        "scroll_refs": [{"file": str(scroll_file), "position": position}],
        "captured_at": "2026-09-29T21:05:00+07:00",
    }
    rec.update(over)
    return rec


def fb_container(**over):
    rec = {
        "record_type": "container", "platform": "facebook", "kind": "group",
        "name": "ROXANA PLAZA - HÀNH TRÌNH ĐÒI NHÀ", "url": "https://www.facebook.com/groups/427692059062534/",
        "privacy": "private", "joined": "no", "scan_mode": "full", "topic_dedicated": True,
        "member_count": 2425, "member_count_at": "2026-09-29T20:00:00+07:00",
    }
    rec.update(over)
    return rec
