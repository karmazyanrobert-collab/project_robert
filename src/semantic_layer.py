from __future__ import annotations

from typing import Any

import pandas as pd

from src.config import WAREHOUSE_PATH
from src.warehouse import get_connection


def _where(filters: dict[str, Any] | None, alias: str = "") -> tuple[str, list[Any]]:
    filters = filters or {}
    p = f"{alias}." if alias else ""
    clauses, params = [], []
    if filters.get("faculty") and filters["faculty"] != "All":
        clauses.append(f"{p}faculty = ?")
        params.append(filters["faculty"])
    if filters.get("group_name") and filters["group_name"] != "All":
        clauses.append(f"{p}group_name = ?")
        params.append(filters["group_name"])
    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


def _date_where(filters: dict[str, Any] | None, column: str = "event_ts") -> tuple[str, list[Any]]:
    base, params = _where(filters)
    clauses = [base.replace(" WHERE ", "")] if base else []
    if filters and filters.get("start_date"):
        clauses.append(f"{column} >= ?")
        params.append(str(filters["start_date"]))
    if filters and filters.get("end_date"):
        clauses.append(f"{column} <= ?")
        params.append(str(filters["end_date"]) + " 23:59:59")
    return (" WHERE " + " AND ".join(clauses) if clauses else "", params)


def query_df(sql: str, params: list[Any] | None = None) -> pd.DataFrame:
    if not WAREHOUSE_PATH.exists():
        return pd.DataFrame()
    with get_connection(read_only=True) as con:
        return con.execute(sql, params or []).fetchdf()


def get_filter_options() -> tuple[list[str], dict[str, list[str]]]:
    df = query_df("SELECT DISTINCT faculty, group_name FROM student_performance_gold ORDER BY faculty, group_name")
    if df.empty:
        return [], {}
    return df["faculty"].unique().tolist(), {f: df.loc[df["faculty"] == f, "group_name"].tolist() for f in df["faculty"].unique()}


def get_kpi_summary(filters: dict[str, Any] | None = None) -> dict[str, Any]:
    where, params = _where(filters)
    sql = f"""
        SELECT COUNT(*) total_students, AVG(avg_grade) average_grade, SUM(risk_flag) risk_students,
               AVG(completion_rate) average_completion_rate, AVG(engagement_score) average_engagement_score
        FROM student_performance_gold {where}
    """
    df = query_df(sql, params)
    lms_where, lms_params = _date_where(filters)
    active = query_df(f"SELECT SUM(active_students) active_lms_students FROM lms_engagement_gold {lms_where}", lms_params)
    row = df.iloc[0].to_dict() if not df.empty else {}
    total = row.get("total_students") or 0
    risk = row.get("risk_students") or 0
    row["risk_share"] = (risk / total) if total else 0
    row["active_lms_students"] = int(active.iloc[0]["active_lms_students"] or 0) if not active.empty else 0
    return row


def get_faculty_metrics() -> pd.DataFrame:
    return query_df("SELECT * FROM faculty_performance_gold ORDER BY avg_grade DESC")


def get_group_metrics(faculty: str | None = None) -> pd.DataFrame:
    if faculty and faculty != "All":
        return query_df("SELECT * FROM group_performance_gold WHERE faculty = ? ORDER BY avg_grade DESC", [faculty])
    return query_df("SELECT * FROM group_performance_gold ORDER BY faculty, avg_grade DESC")


def get_student_details(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    where, params = _where(filters)
    return query_df(f"SELECT student_id, full_name, faculty, group_name, avg_grade, completion_rate, engagement_score, attendance_score, risk_flag FROM student_performance_gold {where} ORDER BY avg_grade DESC", params)


def get_risk_students(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    where, params = _where(filters)
    connector = " AND " if where else " WHERE "
    return query_df(f"SELECT student_id, full_name, faculty, group_name, avg_grade, completion_rate, engagement_score, risk_flag FROM student_performance_gold {where}{connector} risk_flag = 1 ORDER BY avg_grade ASC LIMIT 100", params)


def get_feature_store_preview(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    where, params = _where(filters, alias="sp")
    return query_df(
        f"""
        SELECT sf.student_id, sf.avg_grade, sf.completion_rate, sf.engagement_score,
               sf.attendance_score, sf.risk_flag, sp.faculty, sp.group_name, sp.full_name
        FROM student_features sf
        JOIN student_performance_gold sp USING (student_id)
        {where}
        ORDER BY sf.risk_flag DESC, sf.avg_grade ASC
        LIMIT 100
        """,
        params,
    )


def get_lms_metrics(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    where, params = _date_where(filters)
    return query_df(f"SELECT * FROM lms_engagement_gold {where} ORDER BY event_ts", params)


def get_room_utilization() -> pd.DataFrame:
    return query_df("SELECT * FROM room_utilization_gold ORDER BY utilization_rate DESC LIMIT 100")


def get_data_quality_report() -> pd.DataFrame:
    return query_df("SELECT * FROM data_quality_report ORDER BY status, table_name")


def get_streaming_metrics(filters: dict[str, Any] | None = None) -> dict[str, pd.DataFrame]:
    if not WAREHOUSE_PATH.exists():
        return {"events": pd.DataFrame(), "metrics": pd.DataFrame(), "summary": pd.DataFrame()}
    where, params = _date_where(filters)
    events = query_df(f"SELECT * FROM streaming_events {where} ORDER BY event_ts DESC LIMIT 20", params)
    summary = query_df(
        f"""
        SELECT COALESCE(COUNT(*) / GREATEST(DATE_DIFF('minute', MIN(event_ts), MAX(event_ts)), 1), 0) AS events_per_minute,
               COALESCE(COUNT(DISTINCT student_id) FILTER (WHERE event_ts >= NOW() - INTERVAL 5 MINUTE), 0) AS active_students_last_5m,
               COALESCE(COUNT(*) FILTER (WHERE event_type = 'assignment_submission' AND event_ts >= NOW() - INTERVAL 5 MINUTE), 0) AS assignment_submissions_last_5m,
               COALESCE(COUNT(*) FILTER (WHERE event_type = 'building_entry' AND event_ts >= NOW() - INTERVAL 5 MINUTE), 0) AS building_entries_last_5m
        FROM streaming_events
        {where}
        """,
        params,
    )
    metrics = query_df("SELECT * FROM streaming_metrics ORDER BY metric_ts DESC LIMIT 20")
    return {"events": events, "metrics": metrics, "summary": summary}


def get_streaming_event_count() -> int:
    df = query_df("SELECT COUNT(*) AS events_count FROM streaming_events")
    return int(df.iloc[0]["events_count"] or 0) if not df.empty else 0
