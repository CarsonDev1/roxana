"""Record schema: enum values, Vietnamese display labels, classification descriptions and validate()."""
from __future__ import annotations

LABELS: dict[str, dict[str, str]] = {
    "origin": {"scan": "Quét", "legacy": "Từ file cũ"},
    "platform": {"facebook": "Facebook", "web": "Web / Báo chí", "youtube": "YouTube", "tiktok": "TikTok"},
    "content_type": {"post": "Bài viết", "shared_post": "Bài chia sẻ", "photo": "Ảnh", "video": "Video",
                     "reel": "Reel", "live": "Phát trực tiếp", "article": "Bài báo"},
    "url_kind": {"permalink": "Link riêng của bài", "container_only": "Chỉ có link nhóm", "none": "Không có link"},
    "author_kind": {"person": "Cá nhân", "page": "Trang", "anonymous": "Thành viên ẩn danh", "unknown": "Không rõ"},
    "posted_at_precision": {"exact": "Chính xác", "day": "Theo ngày", "month": "Theo tháng", "year": "Chỉ năm",
                            "relative_estimate": "Ước lượng (thời gian tương đối)", "unknown": "Không rõ"},
    "tone": {"tich_cuc": "Tích cực", "trung_lap": "Trung lập", "tieu_cuc": "Tiêu cực", "gay_gat": "Gay gắt"},
    "claim_type": {"van_ban": "Có văn bản kèm", "cao_buoc": "Cáo buộc", "keu_goi": "Kêu gọi",
                   "thong_tin": "Thông tin", "tin_don": "Tin đồn", "y_kien": "Ý kiến", "hoi_dap": "Hỏi đáp"},
    "importance": {"cao": "Cao", "trung_binh": "Trung bình", "thap": "Thấp"},
    "topics": {"ban_chui": "Bán chui", "tang_gia_ky_lai": "Tăng giá / ký lại HĐ", "cham_ban_giao": "Chậm bàn giao",
               "thanh_tra": "Thanh tra", "toa_an": "Toà án", "cong_an_to_giac": "Công an / tố giác",
               "tuan_hanh": "Tuần hành", "doi_thoai": "Đối thoại", "tranh_chap_noi_bo": "Tranh chấp nội bộ",
               "xay_sai_phep": "Xây sai phép", "hoan_tien": "Hoàn tiền", "khac": "Khác"},
    "container_kind": {"group": "Nhóm", "page": "Trang", "channel": "Kênh"},
    "privacy": {"public": "Công khai", "private": "Kín", "unknown": "Không rõ"},
    "joined": {"yes": "Đã tham gia", "no": "Chưa tham gia", "pending": "Đang chờ duyệt", "unknown": "Không rõ"},
    "scan_mode": {"full": "Quét toàn bộ", "keyword": "Theo từ khoá"},
    "scope": {"global": "Toàn nền tảng", "container": "Trong nhóm/trang"},
    "section": {"posts": "Bài viết", "groups": "Nhóm", "pages": "Trang", "videos": "Video", "photos": "Ảnh",
                "hashtag": "Hashtag", "group_feed": "Feed nhóm", "page_feed": "Feed trang",
                "in_group_search": "Tìm trong nhóm"},
    "recheck_status": {"active": "Còn", "edited": "Đã sửa", "deleted": "Đã xoá", "unavailable": "Không truy cập được"},
    "evidence_kind": {"post": "Thân bài", "attach": "Đính kèm", "cscroll": "Ảnh cuộn bình luận", "comment": "Bình luận"},
    "reliability": {"bao_chi": "Báo chí chính thống", "van_ban": "Có văn bản chính thức",
                    "mxh": "Mạng xã hội — chưa kiểm chứng"},
}

DESCRIPTIONS: dict[str, dict[str, str]] = {
    "tone": {
        "tich_cuc": "Khen, bênh vực, ghi nhận các bên được nhắc",
        "trung_lap": "Đưa tin, hỏi, thông báo — không bày tỏ thái độ",
        "tieu_cuc": "Phê phán, phản đối, bất bình bằng lời lẽ bình thường",
        "gay_gat": "Chửi bới, xúc phạm, đe doạ, dùng từ thô tục",
    },
    "claim_type": {
        "van_ban": "Kèm văn bản/tài liệu (giấy mời, văn bản toà, kết luận thanh tra, hợp đồng)",
        "cao_buoc": "Quy kết hành vi sai trái cho người/tổ chức cụ thể",
        "keu_goi": "Kêu gọi hành động (tố cáo, tập trung, ký đơn…)",
        "thong_tin": "Tường thuật sự kiện, cập nhật tiến trình",
        "tin_don": "Thông tin không nguồn, \"nghe nói\"",
        "y_kien": "Bày tỏ quan điểm, cảm xúc",
        "hoi_dap": "Hỏi hoặc trả lời câu hỏi",
    },
    "importance": {
        "cao": ("Kèm văn bản chính thức · nêu đích danh một bên chính kèm cáo buộc · tin mới về tiến trình "
                "pháp lý/hành chính · do admin nhóm hoặc một bên chính đăng · tương tác ≥ 100 · "
                "bình luận ≥ 20 lượt thích"),
        "trung_binh": "Nhắc tới vụ việc hoặc các bên với nội dung có thông tin/ý kiến cụ thể",
        "thap": "Ngắn, không thêm thông tin (\"hóng\", \"+1\", sticker) — vẫn được ghi đủ",
    },
}

ENUMS: dict[str, set[str]] = {name: set(values) for name, values in LABELS.items()}
ENUMS["record_type"] = {"source", "comment", "container", "search_log", "recheck", "exclusion", "event"}

EXCLUSION_FIELDS = {"record_type", "url", "excerpt", "keywords_matched", "reason", "search_log_id", "notes",
                    "platform", "origin", "run_id", "captured_at", "id", "recorded_at", "dedupe_key"}

CONTAINER_UPDATABLE = {"privacy", "joined", "scan_mode", "member_count", "member_count_at", "last_scanned_at",
                       "topic_dedicated", "notes", "name"}

REQUIRED: dict[str, dict[str, list[str]]] = {
    "source": {"always": ["platform", "content_type", "url", "url_kind", "author_name", "author_kind",
                          "posted_at_raw", "posted_at_precision", "text", "keywords_matched", "importance",
                          "captured_at"],
               "scan": ["tone", "claim_type", "importance_reason"]},
    "comment": {"always": ["source_id", "depth", "author_name", "author_kind", "posted_at_raw",
                           "posted_at_precision", "text", "tone", "claim_type", "importance", "scroll_refs",
                           "captured_at"]},
    "container": {"always": ["platform", "kind", "name", "url", "privacy", "joined", "scan_mode",
                             "topic_dedicated"]},
    "search_log": {"always": ["platform", "scope", "section", "query", "started_at", "results_seen",
                              "results_new", "reached_end"]},
    "recheck": {"always": ["target_id", "checked_at", "status"]},
    "exclusion": {"always": ["url", "excerpt", "keywords_matched", "reason"]},
    "event": {"always": ["date_raw", "description", "reliability"]},
}

SCALAR_ENUMS = {"origin": "origin", "platform": "platform", "content_type": "content_type", "url_kind": "url_kind",
                "author_kind": "author_kind", "posted_at_precision": "posted_at_precision", "tone": "tone",
                "claim_type": "claim_type", "importance": "importance", "privacy": "privacy", "joined": "joined",
                "scan_mode": "scan_mode", "scope": "scope", "section": "section", "reliability": "reliability"}
TYPE_ENUMS = {"container": {"kind": "container_kind"}, "recheck": {"status": "recheck_status"}}


def label(enum_name: str, value) -> str:
    if value is None:
        return ""
    return LABELS.get(enum_name, {}).get(value, value)


def _missing(rec: dict, field: str) -> bool:
    return rec.get(field) is None


def _enum_error(field: str, value, enum_name: str) -> str:
    return f"{field}={value!r} không hợp lệ (cho phép: {', '.join(sorted(ENUMS[enum_name]))})"


def validate(rec: dict, config: dict | None = None) -> list[str]:
    rtype = rec.get("record_type")
    if rtype not in ENUMS["record_type"]:
        return [f"record_type không hợp lệ: {rtype!r}"]
    origin = rec.get("origin", "scan")
    errors: list[str] = []

    required = REQUIRED[rtype]
    for field in required.get("always", []) + required.get(origin, []):
        if _missing(rec, field):
            errors.append(f"Thiếu trường bắt buộc: {field}")

    for field, enum_name in {**SCALAR_ENUMS, **TYPE_ENUMS.get(rtype, {})}.items():
        value = rec.get(field)
        if value is not None and value not in ENUMS[enum_name]:
            errors.append(_enum_error(field, value, enum_name))
    bad_topics = [t for t in rec.get("topics") or [] if t not in ENUMS["topics"]]
    if bad_topics:
        errors.append(f"topics không hợp lệ: {', '.join(map(str, bad_topics))}")

    if config is not None:
        groups = {g["id"] for g in config.get("keyword_groups", [])}
        bad = [k for k in rec.get("keywords_matched") or [] if k not in groups]
        if bad:
            errors.append(f"keywords_matched không có trong config: {', '.join(map(str, bad))}")
        parties = {p["id"] for p in config.get("key_parties", [])}
        bad = [p for p in rec.get("entities_mentioned") or [] if p not in parties]
        if bad:
            errors.append(f"entities_mentioned không có trong key_parties: {', '.join(map(str, bad))}")

    if rec.get("text") is not None and not isinstance(rec["text"], str):
        errors.append("text phải là chuỗi")
    shape = [f"{field} phải là danh sách"
             for field in ("attachments", "evidence", "scroll_refs", "keywords_matched", "entities_mentioned", "topics")
             if rec.get(field) is not None and not isinstance(rec[field], list)]
    shape += [f"{field} phải là object" for field in ("metrics", "shared_from", "filters", "updates")
              if rec.get(field) is not None and not isinstance(rec[field], dict)]
    if isinstance(rec.get("attachments"), list) and any(not isinstance(a, dict) for a in rec["attachments"]):
        shape.append("attachments[] phải là object {kind, description, transcribed_text, url}")
    if shape:
        return errors + shape

    evidence = rec.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, list):
            errors.append("evidence phải là danh sách")
        else:
            for i, item in enumerate(evidence):
                if not isinstance(item, dict):
                    errors.append(f"evidence[{i}] phải là object {{file, kind, shows}}")
                    continue
                if not item.get("file"):
                    errors.append(f"evidence[{i}] thiếu file")
                if item.get("kind") not in ENUMS["evidence_kind"]:
                    errors.append(f"evidence[{i}]: " + _enum_error("kind", item.get("kind"), "evidence_kind"))
                if not item.get("shows"):
                    errors.append(f"evidence[{i}] thiếu shows (ảnh chụp phần nào)")

    if rtype == "source" and origin == "scan":
        if not rec.get("evidence"):
            errors.append("Bài thu thập (origin=scan) phải có ít nhất 1 ảnh trong evidence")
        if _missing(rec, "snapshot_text") and _missing(rec, "snapshot_file"):
            errors.append("Thiếu snapshot_text hoặc snapshot_file (bản chữ gốc của trang)")
        if rec.get("url_kind") in ("permalink", "container_only") and not rec.get("url"):
            errors.append("url_kind yêu cầu url không rỗng")

    if rtype == "comment":
        depth = rec.get("depth")
        if not isinstance(depth, int) or not 1 <= depth <= 3:
            errors.append("depth phải là 1, 2 hoặc 3")
        elif depth > 1 and _missing(rec, "parent_comment_id"):
            errors.append("Trả lời (depth > 1) phải có parent_comment_id")
    refs = rec.get("scroll_refs")
    if rtype in ("comment", "recheck") and refs is not None:  # recheck: trỏ bình luận sang ảnh cuộn chụp lại
        if not isinstance(refs, list) or not refs:
            errors.append("scroll_refs phải có ít nhất 1 ảnh cuộn")
        else:
            for i, ref in enumerate(refs):
                if not isinstance(ref, dict) or not ref.get("file") or not isinstance(ref.get("position"), int) or ref["position"] < 1:
                    errors.append(f"scroll_refs[{i}] cần file và position (số nguyên ≥ 1)")
    if rtype == "comment":
        if rec.get("importance") == "cao":
            if not rec.get("evidence"):
                errors.append("Bình luận mức cao phải có ảnh chụp riêng trong evidence")
            if not rec.get("importance_reason"):
                errors.append("Bình luận mức cao cần importance_reason")

    if rtype == "recheck":
        if rec.get("status") == "edited" and _missing(rec, "new_text"):
            errors.append("recheck status=edited phải có new_text")
        updates = rec.get("updates")
        if updates is not None:
            bad = set(updates) - CONTAINER_UPDATABLE
            if bad:
                errors.append(f"updates chỉ được chứa {', '.join(sorted(CONTAINER_UPDATABLE))}; "
                              f"không được: {', '.join(sorted(bad))}")

    if rtype == "exclusion":
        if len(rec.get("excerpt") or "") > 100:
            errors.append("excerpt tối đa 100 ký tự")
        if {"author_name", "author_url"} & rec.keys():
            errors.append("exclusion không được ghi tên người đăng (author_name/author_url)")
        extra = set(rec) - EXCLUSION_FIELDS
        if extra:
            errors.append(f"exclusion chỉ được có {', '.join(sorted(EXCLUSION_FIELDS))} — không ghi ảnh, "
                          f"bản chữ hay thông tin người đăng; bỏ: {', '.join(sorted(extra))}")

    return errors
