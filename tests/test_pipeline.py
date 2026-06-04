from pathlib import Path

import duckdb

from src.config import WAREHOUSE_PATH
from src.pipeline import run_pipeline
from src.semantic_layer import get_kpi_summary, get_student_details


def test_pipeline_creates_warehouse_and_gold_tables():
    run_pipeline(regenerate=True)
    assert WAREHOUSE_PATH.exists()
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


def test_semantic_layer_returns_kpi_and_filters_change_rows():
    run_pipeline(regenerate=True)
    kpi = get_kpi_summary({"faculty": "All", "group_name": "All"})
    assert kpi["total_students"] == 500
    all_students = get_student_details({"faculty": "All", "group_name": "All"})
    faculty_students = get_student_details({"faculty": "Computer Science", "group_name": "All"})
    group_students = get_student_details({"faculty": "Computer Science", "group_name": "COM-11"})
    assert len(all_students) > len(faculty_students) > len(group_students) > 0
