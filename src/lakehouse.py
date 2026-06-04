from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import BRONZE_DIR, GOLD_DIR, SILVER_DIR, WAREHOUSE_PATH

LAYER_PURPOSES = {
    "students": "справочник студентов",
    "courses": "справочник курсов",
    "grades": "оценки и экзамены",
    "assignments": "задания и результаты",
    "lms_activity": "события LMS",
    "submissions": "отправки заданий",
    "material_views": "просмотры материалов",
    "buildings": "корпуса кампуса",
    "rooms": "аудитории",
    "room_events": "события в аудиториях",
    "student_performance_gold": "витрина успеваемости студентов",
    "faculty_performance_gold": "витрина факультетов",
    "group_performance_gold": "витрина групп",
    "lms_engagement_gold": "витрина вовлечённости LMS",
    "room_utilization_gold": "витрина загрузки аудиторий",
    "student_features": "признаки студентов для ML и risk scoring",
}


def _count_parquet_rows(path: Path) -> int:
    try:
        return int(len(pd.read_parquet(path)))
    except Exception:
        return 0


def build_lakehouse_inventory() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for layer_name, directory in (("Bronze", BRONZE_DIR), ("Silver", SILVER_DIR), ("Gold", GOLD_DIR)):
        for path in sorted(directory.glob("*.parquet")):
            table_name = path.stem
            rows.append(
                {
                    "слой": layer_name,
                    "файл": str(path.relative_to(BRONZE_DIR.parents[1])),
                    "количество строк": _count_parquet_rows(path),
                    "назначение": LAYER_PURPOSES.get(table_name, "демонстрационная таблица"),
                }
            )
    rows.append(
        {
            "слой": "Warehouse",
            "файл": str(WAREHOUSE_PATH.relative_to(BRONZE_DIR.parents[1])),
            "количество строк": "—",
            "назначение": "DuckDB warehouse с Gold-витринами, DQ report и streaming tables",
        }
    )
    return pd.DataFrame(rows)


def build_lakehouse_lineage() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "источник": "students",
                "bronze table": "bronze/students.parquet",
                "silver table": "silver/students.parquet",
                "gold table": "student_performance_gold",
                "business purpose": "анализ студентов и drill-down по группам",
            },
            {
                "источник": "grades",
                "bronze table": "bronze/grades.parquet",
                "silver table": "silver/grades.parquet",
                "gold table": "student_performance_gold",
                "business purpose": "расчёт среднего балла и академического риска",
            },
            {
                "источник": "assignments",
                "bronze table": "bronze/assignments.parquet",
                "silver table": "silver/assignments.parquet",
                "gold table": "student_features",
                "business purpose": "completion rate и признаки для ML",
            },
            {
                "источник": "lms_activity",
                "bronze table": "bronze/lms_activity.parquet",
                "silver table": "silver/lms_activity.parquet",
                "gold table": "lms_engagement_gold",
                "business purpose": "анализ вовлечённости студентов в LMS",
            },
            {
                "источник": "room_events",
                "bronze table": "bronze/room_events.parquet",
                "silver table": "silver/room_events.parquet",
                "gold table": "room_utilization_gold",
                "business purpose": "оценка загрузки аудиторий и корпусов",
            },
        ]
    )


def build_quality_row_delta() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for bronze_path in sorted(BRONZE_DIR.glob("*.parquet")):
        silver_path = SILVER_DIR / bronze_path.name
        if silver_path.exists():
            bronze_rows = _count_parquet_rows(bronze_path)
            silver_rows = _count_parquet_rows(silver_path)
            rows.append(
                {
                    "таблица": bronze_path.stem,
                    "Bronze rows": bronze_rows,
                    "Silver rows": silver_rows,
                    "Removed invalid rows": max(bronze_rows - silver_rows, 0),
                }
            )
    return pd.DataFrame(rows)
