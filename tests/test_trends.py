import json

from trends import keyword_of, parse_timeline, summarize

BODY = ")]}',\n" + json.dumps({"default": {"timelineData": [
    {"time": "1735689600", "value": [10]},  # 2025-01
    {"time": "1738368000", "value": [80]},  # 2025-02
    {"time": "1740787200", "value": [40]},  # 2025-03
    {"time": "1743465600", "value": [100], "isPartial": True}]}})


def test_parse_timeline_months_and_partial():
    pts = parse_timeline(BODY)
    assert [(p["date"], p["value"], p["partial"]) for p in pts] == [
        ("2025-01", 10, False), ("2025-02", 80, False), ("2025-03", 40, False), ("2025-04", 100, True)]


def test_summarize_ignores_the_partial_current_month():
    s = summarize(parse_timeline(BODY))
    assert s["peak_month"] == "2025-02" and s["peak_value"] == 80
    assert s["last_month"] == "2025-03" and s["last_value"] == 40


def test_summarize_no_data():
    assert summarize([])["peak_month"] is None


def test_keyword_skips_hashtags():
    assert keyword_of({"terms": ["#roxanaplaza", "Roxana Plaza"]}) == "Roxana Plaza"
    assert keyword_of({"terms": ["#x"]}) is None
