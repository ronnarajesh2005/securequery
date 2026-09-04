import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.analytics import build_analytics


MOCK_RESULTS = [
    {"group_key": "H1-2023-Diabetes", "hospital": "H1", "year": 2023, "disease": "Diabetes", "value": 120},
    {"group_key": "H1-2024-Diabetes", "hospital": "H1", "year": 2024, "disease": "Diabetes", "value": 140},
    {"group_key": "H2-2023-Diabetes", "hospital": "H2", "year": 2023, "disease": "Diabetes", "value": 95},
]


def test_stats_match_manual_calculation():
    result = build_analytics(MOCK_RESULTS)
    assert result["stats"]["count"] == 3
    assert result["stats"]["min"] == 95
    assert result["stats"]["max"] == 140
    assert result["stats"]["avg"] == round((120 + 140 + 95) / 3, 2)


def test_cross_hospital_table_has_all_hospitals():
    result = build_analytics(MOCK_RESULTS)
    table = next(t for t in result["tables"] if t["title"] == "Cross-hospital comparison")
    hospitals_in_table = {row["hospital"] for row in table["data"]}
    assert hospitals_in_table == {"H1", "H2"}


def test_charts_are_valid_objects():
    result = build_analytics(MOCK_RESULTS)
    assert len(result["charts"]) > 0
    for chart in result["charts"]:
        assert chart["figure"] is not None


def test_empty_results():
    result = build_analytics([])
    assert result["stats"]["count"] == 0