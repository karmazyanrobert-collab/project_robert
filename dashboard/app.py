from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR, WAREHOUSE_PATH
from src.pipeline import run_pipeline
from src.semantic_layer import (
    get_data_quality_report,
    get_faculty_metrics,
    get_feature_store_preview,
    get_filter_options,
    get_group_metrics,
    get_kpi_summary,
    get_lms_metrics,
    get_risk_students,
    get_room_utilization,
    get_streaming_metrics,
    get_student_details,
)
from src.streaming_demo import generate_streaming_events

st.set_page_config(page_title="University Data Platform Demo", layout="wide")


def ensure_warehouse() -> None:
    if not WAREHOUSE_PATH.exists():
        with st.spinner("First launch: generating data, Bronze/Silver/Gold and DuckDB warehouse..."):
            run_pipeline(regenerate=True)


def metric_card(label: str, value, fmt: str = "{}") -> None:
    st.metric(label, fmt.format(value if pd.notna(value) else 0))


ensure_warehouse()

st.sidebar.header("Controls")
if st.sidebar.button("Run / Regenerate pipeline", use_container_width=True):
    with st.spinner("Regenerating full platform..."):
        run_pipeline(regenerate=True)
    st.success("Pipeline completed")
    st.rerun()

if st.sidebar.button("Generate streaming events", use_container_width=True):
    count = generate_streaming_events()
    st.sidebar.success(f"Generated {count} streaming events")

if st.sidebar.button("Refresh dashboard", use_container_width=True):
    st.rerun()

faculties, groups_by_faculty = get_filter_options()
selected_faculty = st.sidebar.selectbox("Faculty", ["All"] + faculties)
available_groups = [] if selected_faculty == "All" else groups_by_faculty.get(selected_faculty, [])
selected_group = st.sidebar.selectbox("Group", ["All"] + available_groups)
default_start = date.today() - timedelta(days=120)
default_end = date.today()
date_range = st.sidebar.date_input("Date range", value=(default_start, default_end))
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

filters = {"faculty": selected_faculty, "group_name": selected_group, "start_date": start_date, "end_date": end_date}

st.title("University Data Platform Demo")
st.subheader("Architecture")
st.code("Source systems → Bronze → Data Quality → Silver → Gold → Feature Store → Semantic Layer → Dashboard")
st.write(
    "Autonomous Streamlit Cloud demo: if `data/warehouse.duckdb` is missing, the app generates synthetic university data, "
    "persists Bronze/Silver/Gold parquet layers, loads DuckDB, and renders analytics without Docker or external services."
)

kpi = get_kpi_summary(filters)
st.subheader("KPI")
cols = st.columns(6)
with cols[0]:
    metric_card("Total students", int(kpi.get("total_students") or 0))
with cols[1]:
    metric_card("Average grade", float(kpi.get("average_grade") or 0), "{:.1f}")
with cols[2]:
    metric_card("Risk students", int(kpi.get("risk_students") or 0))
with cols[3]:
    metric_card("Risk share", float(kpi.get("risk_share") or 0) * 100, "{:.1f}%")
with cols[4]:
    metric_card("Avg completion", float(kpi.get("average_completion_rate") or 0) * 100, "{:.1f}%")
with cols[5]:
    metric_card("Active LMS students", int(kpi.get("active_lms_students") or 0))

students = get_student_details(filters)
risk_students = get_risk_students(filters)
features = get_feature_store_preview(filters)
lms = get_lms_metrics(filters)
rooms = get_room_utilization()
dq = get_data_quality_report()
streaming = get_streaming_metrics(filters)

st.subheader("Drill-down Analytics")
if selected_faculty == "All":
    st.info("Faculty = All: showing faculty-level analytics.")
    drill = get_faculty_metrics()
    group_col = "faculty"
elif selected_group == "All":
    st.info(f"Faculty selected ({selected_faculty}): showing group-level analytics.")
    drill = get_group_metrics(selected_faculty)
    group_col = "group_name"
else:
    st.info(f"Group selected ({selected_group}): showing student-level analytics.")
    drill = students.head(50)
    group_col = "full_name"

c1, c2 = st.columns(2)
with c1:
    if not drill.empty:
        st.plotly_chart(px.bar(drill, x=group_col, y="avg_grade", title="Average grade by faculty/group/student"), use_container_width=True)
with c2:
    risk_chart_df = get_group_metrics(selected_faculty) if selected_faculty != "All" else get_faculty_metrics()
    if not risk_chart_df.empty:
        st.plotly_chart(px.bar(risk_chart_df, x=("group_name" if selected_faculty != "All" else "faculty"), y="risk_share", title="Risk students share"), use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    if not drill.empty and "completion_rate" in drill.columns:
        st.plotly_chart(px.bar(drill.head(30), x=group_col, y="completion_rate", title="Assignment completion rate"), use_container_width=True)
with c4:
    if not lms.empty:
        lms_event = lms.groupby("event_type", as_index=False)["events"].sum()
        st.plotly_chart(px.pie(lms_event, names="event_type", values="events", title="LMS activity by event type"), use_container_width=True)

c5, c6 = st.columns(2)
with c5:
    if not students.empty:
        st.plotly_chart(px.histogram(students, x="engagement_score", nbins=20, title="Engagement score distribution"), use_container_width=True)
with c6:
    if not rooms.empty:
        st.plotly_chart(px.bar(rooms.head(20), x="room_name", y="utilization_rate", color="building_name", title="Room utilization"), use_container_width=True)

st.subheader("Tables")
t1, t2 = st.tabs(["Students", "Risk students"])
with t1:
    st.dataframe(students, use_container_width=True)
with t2:
    st.dataframe(risk_students, use_container_width=True)

st.subheader("Feature Store Preview")
st.dataframe(features, use_container_width=True)

st.subheader("Data Quality Report")
st.dataframe(dq, use_container_width=True)
st.caption(f"Bronze: `{BRONZE_DIR}` | Silver: `{SILVER_DIR}` | Gold: `{GOLD_DIR}` | DuckDB: `{WAREHOUSE_PATH}`")

st.subheader("Streaming Analytics")
metrics = streaming["metrics"]
events = streaming["events"]
if not metrics.empty:
    latest = metrics.iloc[0]
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Events per minute", f"{latest['events_per_minute']:.1f}")
    s2.metric("Active students last 5 min", int(latest["active_students_last_5m"]))
    s3.metric("Assignment submissions last 5 min", int(latest["assignment_submissions_last_5m"]))
    s4.metric("Building entries last 5 min", int(latest["building_entries_last_5m"]))
    st.line_chart(metrics.sort_values("metric_ts").set_index("metric_ts")[["events_per_minute"]])
else:
    st.warning("No streaming events yet. Click 'Generate streaming events'.")
st.dataframe(events, use_container_width=True)
