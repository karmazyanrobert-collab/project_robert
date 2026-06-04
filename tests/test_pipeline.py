import duckdb

from src.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR, WAREHOUSE_PATH
from src.lakehouse import build_lakehouse_lineage
from src.pipeline import run_pipeline
from src.semantic_layer import get_kpi_summary, get_student_details
from src.streaming_demo import generate_streaming_events


def test_pipeline_creates_duckdb_warehouse_and_layers():
    run_pipeline(regenerate=True)
    assert WAREHOUSE_PATH.exists()
    assert BRONZE_DIR.exists()
    assert SILVER_DIR.exists()
    assert GOLD_DIR.exists()
    assert any(BRONZE_DIR.glob("*.parquet"))
    assert any(SILVER_DIR.glob("*.parquet"))
    assert any(GOLD_DIR.glob("*.parquet"))


def test_gold_tables_are_not_empty():
    run_pipeline(regenerate=True)
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        for table in [
            "student_performance_gold",
            "faculty_performance_gold",
            "group_performance_gold",
            "lms_engagement_gold",
            "room_utilization_gold",
        ]:
            count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count > 0, table


def test_student_features_and_data_quality_report_exist():
    run_pipeline(regenerate=True)
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        feature_count = con.execute("SELECT COUNT(*) FROM student_features").fetchone()[0]
        dq_count = con.execute("SELECT COUNT(*) FROM data_quality_report").fetchone()[0]
    assert feature_count > 0
    assert dq_count > 0


def test_semantic_layer_returns_kpi():
    run_pipeline(regenerate=True)
    kpi = get_kpi_summary({"faculty": "All", "group_name": "All"})
    assert kpi["total_students"] == 500
    assert kpi["average_grade"] > 0
    assert "risk_share" in kpi


def test_faculty_and_group_filters_change_row_counts():
    run_pipeline(regenerate=True)
    all_students = get_student_details({"faculty": "All", "group_name": "All"})
    faculty_students = get_student_details({"faculty": "Computer Science", "group_name": "All"})
    group_students = get_student_details({"faculty": "Computer Science", "group_name": "COM-11"})
    assert len(all_students) > len(faculty_students) > len(group_students) > 0


def test_semantic_layer_accepts_russian_all_filter_value():
    run_pipeline(regenerate=True)
    english_all = get_student_details({"faculty": "All", "group_name": "All"})
    russian_all = get_student_details({"faculty": "Все", "group_name": "Все"})
    assert len(english_all) == len(russian_all) == 500


def test_streaming_event_generation_creates_events():
    run_pipeline(regenerate=True)
    generated = generate_streaming_events(25)
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        events_count = con.execute("SELECT COUNT(*) FROM streaming_events").fetchone()[0]
        metrics_count = con.execute("SELECT COUNT(*) FROM streaming_metrics").fetchone()[0]
    assert generated == 25
    assert events_count >= 25
    assert metrics_count > 0


def test_data_quality_report_contains_pass_and_fail():
    run_pipeline(regenerate=True)
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as con:
        statuses = {row[0] for row in con.execute("SELECT DISTINCT status FROM data_quality_report").fetchall()}
    assert "PASS" in statuses
    assert "FAIL" in statuses


def test_lakehouse_lineage_can_be_built_without_error():
    lineage = build_lakehouse_lineage()
    assert not lineage.empty
    assert {"источник", "bronze table", "silver table", "gold table", "business purpose"}.issubset(lineage.columns)


def test_conflicting_files_have_no_merge_markers():
    conflict_files = [
        "DEMO_SCENARIO.md",
        "README.md",
        "dashboard/app.py",
        "src/data_quality.py",
        "src/semantic_layer.py",
        "tests/test_pipeline.py",
    ]
    for file_name in conflict_files:
        content = open(file_name, encoding="utf-8").read()
        markers = ["<" * 7, "=" * 7, ">" * 7]
        assert all(marker not in content for marker in markers)
