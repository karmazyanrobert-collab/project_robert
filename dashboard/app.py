from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR, WAREHOUSE_PATH
from src.lakehouse import build_lakehouse_inventory, build_lakehouse_lineage, build_quality_row_delta
from src.pipeline import run_pipeline
from src.data_quality import STATUS_LABELS_RU
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
    get_streaming_event_count,
    get_streaming_metrics,
    get_student_details,
)
from src.streaming_demo import generate_streaming_events

st.set_page_config(page_title="University Data Platform Demo", layout="wide")

ALL = "All"
ALL_RU = "Все"


EVENT_TYPE_RU = {
    "login": "вход в LMS",
    "view_material": "просмотр материала",
    "submit_assignment": "отправка задания",
    "quiz_attempt": "попытка теста",
    "forum_post": "сообщение на форуме",
    "lms_click": "клик в LMS",
    "assignment_submission": "отправка задания",
    "building_entry": "вход в корпус",
}

COMPONENT_MAPPING = pd.DataFrame(
    [
        {"Компонент задания": "Object Storage / S3", "Реализация в демо": "локальная структура data/"},
        {"Компонент задания": "Airflow / Prefect", "Реализация в демо": "встроенный Python pipeline"},
        {"Компонент задания": "Kafka", "Реализация в демо": "встроенный генератор потоковых событий"},
        {"Компонент задания": "ClickHouse", "Реализация в демо": "DuckDB"},
        {"Компонент задания": "Grafana", "Реализация в демо": "Streamlit dashboard"},
        {"Компонент задания": "Feast", "Реализация в демо": "таблица student_features"},
        {"Компонент задания": "Cube.js", "Реализация в демо": "Python semantic layer"},
        {"Компонент задания": "Lakehouse", "Реализация в демо": "Bronze/Silver/Gold Parquet + DuckDB"},
        {"Компонент задания": "Great Expectations", "Реализация в демо": "собственный Data Quality framework"},
    ]
)


def ensure_warehouse() -> None:
    if not WAREHOUSE_PATH.exists():
        with st.spinner("Первый запуск: генерируем данные, строим Bronze/Silver/Gold и DuckDB warehouse..."):
            run_pipeline(regenerate=True)


def ensure_demo_streaming_events() -> None:
    if get_streaming_event_count() == 0:
        generate_streaming_events(40)


def ru_status(value: str) -> str:
    return STATUS_LABELS_RU.get(value, value)


def option_label(value: str) -> str:
    return ALL_RU if value == ALL else value


def metric_card(label: str, value, fmt: str = "{}") -> None:
    st.metric(label, fmt.format(value if pd.notna(value) else 0))


def display_df(df: pd.DataFrame, limit: int = 100) -> pd.DataFrame:
    return df.head(limit).copy() if not df.empty else df


def with_russian_event_types(df: pd.DataFrame, column: str = "event_type") -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return df
    result = df.copy()
    result["тип события"] = result[column].map(EVENT_TYPE_RU).fillna(result[column])
    return result


def show_architecture_section() -> None:
    st.subheader("Архитектура платформы")
    st.code(
        "Источники данных\n"
        "→ Bronze-слой\n"
        "→ Проверка качества данных\n"
        "→ Silver-слой\n"
        "→ Gold-слой\n"
        "→ Feature Store\n"
        "→ DuckDB Warehouse\n"
        "→ Semantic Layer\n"
        "→ Streamlit Dashboard"
    )
    st.write(
        "Проект реализован как автономная демонстрационная версия без Docker и внешних сервисов. "
        "В промышленной версии локальные аналоги могут быть заменены на Kafka, Airflow, ClickHouse, "
        "Grafana, Delta Lake/Iceberg и S3."
    )
    st.dataframe(COMPONENT_MAPPING, use_container_width=True, hide_index=True)


def prepare_dq_display(dq: pd.DataFrame) -> pd.DataFrame:
    if dq.empty:
        return dq
    result = dq.copy()
    result["статус"] = result["status_ru"] if "status_ru" in result.columns else result["status"].map(ru_status)
    result = result.rename(
        columns={
            "check_name": "проверка",
            "table_name": "таблица",
            "failed_rows": "ошибочных строк",
            "explanation_ru": "пояснение",
        }
    )
    return result[["проверка", "таблица", "статус", "ошибочных строк", "пояснение"]]


ensure_warehouse()
ensure_demo_streaming_events()

st.sidebar.header("Управление")
if st.sidebar.button("Запустить / пересоздать пайплайн", use_container_width=True):
    with st.spinner("Пересоздаём данные, слои Lakehouse и warehouse..."):
        run_pipeline(regenerate=True)
        generate_streaming_events(40)
    st.session_state["pipeline_success"] = "Пайплайн успешно пересоздан: данные, Bronze/Silver/Gold, DuckDB и демо-поток обновлены."
    st.rerun()

if st.sidebar.button("Сгенерировать потоковые события", use_container_width=True):
    count = generate_streaming_events()
    st.session_state["streaming_success"] = f"Добавлено потоковых событий: {count}. Метрики обновлены."
    st.rerun()

if st.sidebar.button("Обновить дашборд", use_container_width=True):
    st.rerun()

if "pipeline_success" in st.session_state:
    st.sidebar.success(st.session_state.pop("pipeline_success"))
if "streaming_success" in st.session_state:
    st.sidebar.success(st.session_state.pop("streaming_success"))

faculties, groups_by_faculty = get_filter_options()
selected_faculty = st.sidebar.selectbox("Факультет", [ALL] + faculties, format_func=option_label)
available_groups = [] if selected_faculty == ALL else groups_by_faculty.get(selected_faculty, [])
selected_group = st.sidebar.selectbox("Группа", [ALL] + available_groups, format_func=option_label)
default_start = date.today() - timedelta(days=120)
default_end = date.today()
date_range = st.sidebar.date_input("Диапазон дат", value=(default_start, default_end), help="Влияет на события LMS, потоковые события и event-based метрики.")
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

filters = {"faculty": selected_faculty, "group_name": selected_group, "start_date": start_date, "end_date": end_date}

kpi = get_kpi_summary(filters)
students = get_student_details(filters)
risk_students = get_risk_students(filters)
features = get_feature_store_preview(filters)
lms = get_lms_metrics(filters)
rooms = get_room_utilization()
dq = get_data_quality_report()
streaming = get_streaming_metrics(filters)

st.title("University Data Platform Demo")
st.caption("Демонстрационная доменно-ориентированная аналитическая платформа университета")

st.info(
    f"Текущий фильтр: Факультет = {option_label(selected_faculty)} | "
    f"Группа = {option_label(selected_group)} | Даты = {start_date} — {end_date} | "
    f"Количество студентов после фильтрации = {len(students)}"
)

tabs = st.tabs(["Обзор", "Lakehouse", "Качество данных", "Feature Store", "Потоковая аналитика", "Drill-down аналитика", "Документация"])

with tabs[0]:
    show_architecture_section()
    st.subheader("Ключевые показатели")
    st.write("KPI пересчитываются по выбранным фильтрам факультета и группы; даты влияют на событийные LMS-метрики.")
    cols = st.columns(6)
    with cols[0]:
        metric_card("Всего студентов", int(kpi.get("total_students") or 0))
    with cols[1]:
        metric_card("Средний балл", float(kpi.get("average_grade") or 0), "{:.1f}")
    with cols[2]:
        metric_card("Студентов в группе риска", int(kpi.get("risk_students") or 0))
    with cols[3]:
        metric_card("Доля риска", float(kpi.get("risk_share") or 0) * 100, "{:.1f}%")
    with cols[4]:
        metric_card("Средняя доля выполненных заданий", float(kpi.get("average_completion_rate") or 0) * 100, "{:.1f}%")
    with cols[5]:
        metric_card("Средний индекс вовлечённости", float(kpi.get("average_engagement_score") or 0), "{:.1f}")

    st.subheader("Быстрый аналитический обзор")
    c1, c2 = st.columns(2)
    overview_level = get_faculty_metrics() if selected_faculty == ALL else get_group_metrics(selected_faculty)
    overview_x = "faculty" if selected_faculty == ALL else "group_name"
    with c1:
        if not overview_level.empty:
            st.plotly_chart(
                px.bar(overview_level, x=overview_x, y="avg_grade", title="Средний балл по факультетам" if selected_faculty == ALL else "Средний балл по группам", labels={"faculty": "Факультет", "group_name": "Группа", "avg_grade": "Средний балл"}),
                use_container_width=True,
            )
    with c2:
        if not overview_level.empty:
            st.plotly_chart(
                px.bar(overview_level, x=overview_x, y="risk_share", title="Доля студентов в группе риска", labels={"faculty": "Факультет", "group_name": "Группа", "risk_share": "Доля риска"}),
                use_container_width=True,
            )

with tabs[1]:
    st.subheader("Lakehouse: Bronze / Silver / Gold")
    st.write(
        "Bronze — сырые данные из источников. Silver — очищенные и типизированные данные. "
        "Gold — аналитические витрины для отчётности, ML и dashboard."
    )
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Bronze-слой", str(BRONZE_DIR.relative_to(ROOT)))
    p2.metric("Silver-слой", str(SILVER_DIR.relative_to(ROOT)))
    p3.metric("Gold-слой", str(GOLD_DIR.relative_to(ROOT)))
    p4.metric("Warehouse", str(WAREHOUSE_PATH.relative_to(ROOT)))
    st.write("Таблица файлов показывает, какие parquet-таблицы реально созданы в каждом слое.")
    st.dataframe(build_lakehouse_inventory(), use_container_width=True, hide_index=True)
    st.subheader("Lineage: от источников до Gold-витрин")
    st.dataframe(build_lakehouse_lineage(), use_container_width=True, hide_index=True)
    st.warning(
        "В данной демонстрационной версии Lakehouse реализован через Parquet-слои Bronze/Silver/Gold и DuckDB. "
        "Apache Iceberg/Delta Lake не используются, чтобы сохранить автономный запуск в Streamlit Cloud. "
        "В промышленной версии эти слои могут быть перенесены на S3 + Iceberg/Delta Lake для поддержки "
        "ACID-транзакций, time travel и управления метаданными."
    )

with tabs[2]:
    st.subheader("Качество данных")
    st.write(
        "Часть ошибок специально добавлена в сырые данные Bronze-слоя, чтобы показать работу механизма контроля качества. "
        "Ошибки фиксируются в Data Quality Report, после чего на этапе Silver некорректные записи удаляются или исправляются."
    )
    dq_display = prepare_dq_display(dq)
    total_checks = len(dq)
    passed = int((dq["status"] == "PASS").sum()) if not dq.empty else 0
    failed = int((dq["status"] == "FAIL").sum()) if not dq.empty else 0
    success_rate = passed / total_checks * 100 if total_checks else 0
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Всего проверок", total_checks)
    d2.metric("Пройдено", passed)
    d3.metric("Ошибок обнаружено", failed)
    d4.metric("Доля успешных проверок", f"{success_rate:.1f}%")
    st.subheader("Отчёт о качестве данных")
    st.dataframe(dq_display, use_container_width=True, hide_index=True)
    st.subheader("Что произошло после Data Quality")
    st.write("Сравнение Bronze и Silver показывает, какие некорректные строки были удалены при очистке данных.")
    st.dataframe(build_quality_row_delta(), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Feature Store: признаки студентов")
    st.write(
        "В демонстрационной версии Feature Store реализован как таблица student_features в DuckDB и Parquet. "
        "В промышленной версии этот компонент может быть заменён на Feast. Признаки фильтруются по факультету и группе."
    )
    st.markdown(
        "**Признаки для risk_flag:** `avg_grade`, `completion_rate`, `engagement_score`, `attendance_score`. "
        "Студент попадает в группу риска, если средний балл ниже 60, доля выполненных заданий ниже 0.6 "
        "или индекс вовлечённости находится в низком сегменте."
    )
    st.dataframe(display_df(features, 100), use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("Потоковая аналитика")
    st.write(
        "В демонстрационном режиме Kafka заменена встроенным генератором событий. "
        "События записываются в DuckDB и используются для расчёта потоковых метрик. "
        "Кнопка в sidebar добавляет новые события и обновляет метрики."
    )
    summary = streaming.get("summary", pd.DataFrame())
    latest = summary.iloc[0].to_dict() if not summary.empty else {}
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Событий за минуту", f"{float(latest.get('events_per_minute') or 0):.1f}")
    s2.metric("Активные студенты за последние 5 минут", int(latest.get("active_students_last_5m") or 0))
    s3.metric("Отправленные задания за последние 5 минут", int(latest.get("assignment_submissions_last_5m") or 0))
    s4.metric("Входы в корпуса за последние 5 минут", int(latest.get("building_entries_last_5m") or 0))
    events = with_russian_event_types(streaming["events"])
    metrics = streaming["metrics"]
    if not metrics.empty:
        st.line_chart(metrics.sort_values("metric_ts").set_index("metric_ts")[["events_per_minute"]])
    st.subheader("Последние 20 потоковых событий")
    st.dataframe(display_df(events, 20), use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Drill-down аналитика")
    if selected_faculty == ALL:
        st.info("Выбран режим 'Все': графики строятся на уровне факультетов.")
        drill = get_faculty_metrics()
        x_col = "faculty"
        x_label = "Факультет"
    elif selected_group == ALL:
        st.info(f"Выбран факультет {selected_faculty}: графики строятся на уровне групп этого факультета.")
        drill = get_group_metrics(selected_faculty)
        x_col = "group_name"
        x_label = "Группа"
    else:
        st.info(f"Выбрана группа {selected_group}: графики и таблицы показывают уровень студентов.")
        drill = students.head(50)
        x_col = "full_name"
        x_label = "Студент"

    c1, c2 = st.columns(2)
    with c1:
        if not drill.empty:
            st.plotly_chart(px.bar(drill, x=x_col, y="avg_grade", title="Средний балл", labels={x_col: x_label, "avg_grade": "Средний балл"}), use_container_width=True)
    with c2:
        if not drill.empty and "completion_rate" in drill.columns:
            st.plotly_chart(px.bar(drill.head(50), x=x_col, y="completion_rate", title="Выполнение заданий", labels={x_col: x_label, "completion_rate": "Доля выполненных заданий"}), use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        if not lms.empty:
            lms_localized = with_russian_event_types(lms)
            lms_event = lms_localized.groupby("тип события", as_index=False)["events"].sum()
            st.plotly_chart(px.pie(lms_event, names="тип события", values="events", title="Активность LMS"), use_container_width=True)
    with c4:
        if not students.empty:
            st.plotly_chart(px.histogram(students, x="engagement_score", nbins=20, title="Индекс вовлечённости", labels={"engagement_score": "Индекс вовлечённости"}), use_container_width=True)

    if not rooms.empty:
        st.plotly_chart(px.bar(rooms.head(30), x="room_name", y="utilization_rate", color="building_name", title="Загрузка аудиторий", labels={"room_name": "Аудитория", "utilization_rate": "Коэффициент загрузки", "building_name": "Корпус"}), use_container_width=True)

    st.subheader("Отфильтрованные студенты")
    st.dataframe(display_df(students, 100), use_container_width=True, hide_index=True)
    st.subheader("Студенты в группе риска")
    st.dataframe(display_df(risk_students, 100), use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Что показывать на защите")
    st.write(
        "Эта вкладка — краткая шпаргалка для русскоязычной защиты проекта. "
        "Она показывает, в каком порядке демонстрировать возможности платформы."
    )
    st.success("Файлы, которые ранее отображались как конфликтующие, сохранены в единой версии без merge-маркеров и проверяются тестом.")
    st.markdown(
        """
1. Открыть dashboard.
2. Показать архитектурную схему.
3. Показать запуск / пересоздание пайплайна.
4. Показать Lakehouse Bronze/Silver/Gold.
5. Показать Data Quality Report.
6. Объяснить, почему есть FAIL в Bronze: ошибки специально добавлены для демонстрации контроля качества.
7. Показать Gold-витрины и DuckDB Warehouse.
8. Показать Feature Store и признаки `student_features`.
9. Выбрать факультет и группу, показать drill-down.
10. Нажать **Сгенерировать потоковые события**.
11. Показать обновление streaming analytics.
12. Объяснить соответствие требованиям задания через таблицу компонентов.
        """
    )
    st.subheader("Почему это demo без Docker")
    st.write(
        "Streamlit Cloud запускает приложение напрямую по `dashboard/app.py`. Поэтому все компоненты сделаны локальными: "
        "pipeline — на Python, streaming — генератор событий, warehouse — DuckDB, lakehouse — parquet-папки. "
        "Это сохраняет автономность и делает демонстрацию воспроизводимой без локальных команд."
    )
