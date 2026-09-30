import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "mention-monitor" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

BASE_CONFIG = {
    "project_name": "Roxana Plaza",
    "output_file": "Roxana_Tong_hop.xlsx",
    "timezone": "+07:00",
    "keyword_groups": [
        {"id": "roxana", "label": "Roxana Plaza", "terms": ["Roxana Plaza", "Roxana"]},
        {"id": "tuongphong", "label": "CĐT Tường Phong", "terms": ["Tường Phong"]},
        {"id": "lien", "label": "Bà Phạm Thị Ngọc Liên",
         "terms": ["Phạm Thị Ngọc Liên", "Phạm Ngọc Liên"], "requires_context": True},
        {"id": "naviland", "label": "Naviland", "terms": ["Naviland"]},
    ],
    "context_terms": ["Roxana", "Tường Phong", "Naviland"],
    "key_parties": [
        {"id": "tuongphong", "name": "Công ty TNHH XD-DV-TM-Đầu tư BĐS Tường Phong", "label": "Tường Phong",
         "kind": "Doanh nghiệp", "role": "Chủ đầu tư", "keyword_group": "tuongphong", "primary": True},
        {"id": "naviland", "name": "Công ty CP Naviland", "label": "Naviland", "kind": "Doanh nghiệp",
         "role": "Bán 1.082 căn", "keyword_group": "naviland", "primary": True},
        {"id": "lien", "name": "Bà Phạm Thị Ngọc Liên", "label": "Bà Phạm Thị Ngọc Liên", "kind": "Cá nhân",
         "role": "TGĐ Naviland từ 22/1/2021", "keyword_group": "lien", "primary": True},
        {"id": "toaan16", "name": "Toà án Nhân dân Khu vực 16 – TP.HCM", "label": "TAND Khu vực 16",
         "kind": "Cơ quan nhà nước", "role": "Thụ lý vụ án", "primary": False},
    ],
    "containers": [],
    "recheck_policy_days": {"cao": 0, "trung_binh": 30, "thap": 90},
}


@pytest.fixture
def project(tmp_path):
    from common import Project

    (tmp_path / "config.json").write_text(json.dumps(BASE_CONFIG, ensure_ascii=False), encoding="utf-8")
    return Project(tmp_path)


@pytest.fixture
def make_png(tmp_path):
    from PIL import Image

    def _make(name="shot.png", size=(800, 500), color=(200, 30, 30)):
        path = tmp_path / "incoming" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", size, color).save(path)
        return path

    return _make


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    """Dữ liệu mẫu dùng ngày tháng 10/2026; đặt 'bây giờ' sau đó để chốt chặn giờ tương lai không chặn nhầm."""
    from datetime import datetime

    import add_record
    from common import TZ

    monkeypatch.setattr(add_record, "NOW", lambda: datetime(2027, 1, 1, tzinfo=TZ))
