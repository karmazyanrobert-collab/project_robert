from __future__ import annotations

import shutil

import pandas as pd

from src.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR, WAREHOUSE_PATH, ensure_directories
from src.data_generator import generate_university_data
from src.data_quality import run_data_quality
from src.warehouse import load_gold_tables


def _write_layer(tables: dict[str, pd.DataFrame], directory) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(directory / f"{name}.parquet", index=False)


def _clean_silver(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    silver = {name: df.copy() for name, df in tables.items()}
    for name, df in silver.items():
        silver[name] = df.drop_duplicates().dropna().copy()

    silver["students"]["student_id"] = silver["students"]["student_id"].astype(int)
    silver["grades"] = silver["grades"].loc[silver["grades"]["grade"].between(0, 100)].copy()
    silver["grades"]["student_id"] = silver["grades"]["student_id"].astype(int)
    silver["assignments"] = silver["assignments"].loc[silver["assignments"]["score"].between(0, 100)].copy()
    silver["lms_activity"] = silver["lms_activity"].loc[silver["lms_activity"]["duration_minutes"].between(1, 180)].copy()
    silver["rooms"] = silver["rooms"].loc[silver["rooms"]["capacity"] > 0].copy()
    for table_name in ("assignments", "lms_activity", "room_events"):
        for col in ("assigned_at", "due_at", "event_ts"):
            if col in silver[table_name].columns:
                silver[table_name][col] = pd.to_datetime(silver[table_name][col])
    return silver


def _build_gold(s: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    students = s["students"]
    grades = s["grades"].merge(students[["student_id", "faculty", "group_name", "full_name"]], on="student_id")
    assignments = s["assignments"].merge(students[["student_id", "faculty", "group_name"]], on="student_id")
    lms = s["lms_activity"].merge(students[["student_id", "faculty", "group_name"]], on="student_id")

    grade_metrics = grades.groupby("student_id", as_index=False).agg(avg_grade=("grade", "mean"), grades_count=("grade", "count"))
    assignment_metrics = assignments.groupby("student_id", as_index=False).agg(
        assignments_total=("assignment_id", "count"),
        assignments_submitted=("submitted", "sum"),
        avg_assignment_score=("score", "mean"),
    )
    assignment_metrics["completion_rate"] = assignment_metrics["assignments_submitted"] / assignment_metrics["assignments_total"]
    lms_metrics = lms.groupby("student_id", as_index=False).agg(
        lms_events=("event_id", "count"),
        avg_duration_minutes=("duration_minutes", "mean"),
        active_days=("event_ts", lambda x: pd.Series(pd.to_datetime(x).dt.date).nunique()),
    )
    lms_metrics["engagement_score"] = (lms_metrics["lms_events"] / lms_metrics["lms_events"].max() * 70 + lms_metrics["active_days"] / lms_metrics["active_days"].max() * 30).round(2)
    lms_metrics["attendance_score"] = (lms_metrics["active_days"] / lms_metrics["active_days"].max() * 100).round(2)

    student_features = students[["student_id", "full_name", "faculty", "group_name", "year"]].merge(grade_metrics, on="student_id", how="left").merge(assignment_metrics, on="student_id", how="left").merge(lms_metrics, on="student_id", how="left")
    fill_cols = ["avg_grade", "grades_count", "assignments_total", "assignments_submitted", "avg_assignment_score", "completion_rate", "lms_events", "avg_duration_minutes", "active_days", "engagement_score", "attendance_score"]
    student_features[fill_cols] = student_features[fill_cols].fillna(0)
    low_engagement = student_features["engagement_score"] < student_features["engagement_score"].quantile(0.25)
    student_features["risk_flag"] = ((student_features["avg_grade"] < 60) | (student_features["completion_rate"] < 0.6) | low_engagement).astype(int)

    student_performance_gold = student_features.copy()
    faculty_performance_gold = student_features.groupby("faculty", as_index=False).agg(
        students=("student_id", "nunique"), avg_grade=("avg_grade", "mean"), risk_students=("risk_flag", "sum"), completion_rate=("completion_rate", "mean"), engagement_score=("engagement_score", "mean")
    )
    faculty_performance_gold["risk_share"] = faculty_performance_gold["risk_students"] / faculty_performance_gold["students"]
    group_performance_gold = student_features.groupby(["faculty", "group_name"], as_index=False).agg(
        students=("student_id", "nunique"), avg_grade=("avg_grade", "mean"), risk_students=("risk_flag", "sum"), completion_rate=("completion_rate", "mean"), engagement_score=("engagement_score", "mean")
    )
    group_performance_gold["risk_share"] = group_performance_gold["risk_students"] / group_performance_gold["students"]

    lms_engagement_gold = lms.groupby([pd.Grouper(key="event_ts", freq="D"), "faculty", "group_name", "event_type"], as_index=False).agg(events=("event_id", "count"), active_students=("student_id", "nunique"), avg_duration=("duration_minutes", "mean"))
    room_utilization_gold = s["room_events"].merge(s["rooms"], on="room_id").merge(s["buildings"], on="building_id")
    room_utilization_gold = room_utilization_gold.groupby(["building_name", "room_name", "room_type"], as_index=False).agg(events=("room_event_id", "count"), avg_occupancy=("occupancy", "mean"), capacity=("capacity", "max"))
    room_utilization_gold["utilization_rate"] = (room_utilization_gold["avg_occupancy"] / room_utilization_gold["capacity"]).clip(0, 1.5)

    return {
        "student_performance_gold": student_performance_gold,
        "faculty_performance_gold": faculty_performance_gold,
        "group_performance_gold": group_performance_gold,
        "lms_engagement_gold": lms_engagement_gold,
        "room_utilization_gold": room_utilization_gold,
        "student_features": student_features[["student_id", "avg_grade", "completion_rate", "engagement_score", "attendance_score", "risk_flag", "faculty", "group_name", "full_name"]],
    }


def run_pipeline(regenerate: bool = True) -> dict[str, object]:
    ensure_directories()
    if regenerate and WAREHOUSE_PATH.exists():
        WAREHOUSE_PATH.unlink()
    for directory in (BRONZE_DIR, SILVER_DIR, GOLD_DIR):
        if regenerate and directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    bronze = generate_university_data()
    _write_layer(bronze, BRONZE_DIR)
    dq_report = run_data_quality(bronze)
    silver = _clean_silver(bronze)
    _write_layer(silver, SILVER_DIR)
    gold = _build_gold(silver)
    _write_layer(gold, GOLD_DIR)
    load_gold_tables(gold, dq_report)
    return {"bronze_tables": len(bronze), "silver_tables": len(silver), "gold_tables": len(gold), "dq_checks": len(dq_report), "warehouse": str(WAREHOUSE_PATH)}


if __name__ == "__main__":
    print(run_pipeline())
