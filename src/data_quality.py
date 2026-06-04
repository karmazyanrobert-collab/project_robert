from __future__ import annotations

import pandas as pd

from src.config import VALID_LMS_EVENT_TYPES, VALID_ROOM_EVENT_TYPES


def _result(check_name: str, table_name: str, failed_rows: int, message: str, explanation_ru: str) -> dict[str, object]:
    return {
        "check_name": check_name,
        "table_name": table_name,
        "status": "PASS" if failed_rows == 0 else "FAIL",
        "failed_rows": int(failed_rows),
        "message": message,
        "explanation_ru": explanation_ru,
    }


def run_data_quality(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    checks: list[dict[str, object]] = []
    students = tables["students"]
    grades = tables["grades"]
    assignments = tables["assignments"]
    lms = tables["lms_activity"]
    rooms = tables["rooms"]
    room_events = tables["room_events"]

    checks.append(_result("student_id not null", "students", students["student_id"].isna().sum(), "Student primary key must be present.", "Идентификатор студента обязателен."))
    checks.append(_result("student_id unique", "students", students["student_id"].duplicated().sum(), "Student primary key must be unique.", "Идентификатор студента должен быть уникальным."))
    checks.append(_result("grade between 0 and 100", "grades", (~grades["grade"].between(0, 100)).sum(), "Grades outside 0..100 are removed in Silver.", "Оценки за пределами 0..100 специально показывают очистку на Silver-слое."))
    checks.append(_result("assignment score between 0 and 100", "assignments", (~assignments["score"].between(0, 100)).sum(), "Assignment scores outside 0..100 are removed in Silver.", "Баллы за задания должны быть в диапазоне 0..100; некорректные строки удаляются на Silver-слое."))
    checks.append(_result("duration_minutes between 1 and 180", "lms_activity", (~lms["duration_minutes"].between(1, 180)).sum(), "LMS durations must be realistic.", "Длительность LMS-сессии должна быть реалистичной: от 1 до 180 минут."))
    checks.append(_result("capacity > 0", "rooms", (rooms["capacity"] <= 0).sum(), "Rooms must have positive capacity.", "Вместимость аудитории должна быть положительной."))
    lms_bad = (~lms["event_type"].isin(VALID_LMS_EVENT_TYPES)).sum()
    room_bad = (~room_events["event_type"].isin(VALID_ROOM_EVENT_TYPES)).sum()
    checks.append(_result("event_type valid", "lms_activity", lms_bad, "LMS event type must be in the allowed dictionary.", "Тип LMS-события должен входить в утверждённый справочник."))
    checks.append(_result("event_type valid", "room_events", room_bad, "Room event type must be in the allowed dictionary.", "Тип события аудитории должен входить в утверждённый справочник."))
    return pd.DataFrame(checks)
