from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from src.config import FACULTIES, GROUPS_BY_FACULTY, RANDOM_SEED, VALID_LMS_EVENT_TYPES, VALID_ROOM_EVENT_TYPES

fake = Faker()
Faker.seed(RANDOM_SEED)


def _date_range(rng: np.random.Generator, start_days_ago: int = 180, size: int = 1) -> list[datetime]:
    now = datetime.now().replace(microsecond=0)
    offsets = rng.integers(0, start_days_ago * 24 * 60, size=size)
    return [now - timedelta(minutes=int(offset)) for offset in offsets]


def generate_university_data(seed: int = RANDOM_SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    fake.seed_instance(seed)

    students = []
    all_groups = []
    for faculty, groups in GROUPS_BY_FACULTY.items():
        all_groups.extend((faculty, group) for group in groups)
    for student_id in range(1, 501):
        faculty, group_name = all_groups[(student_id - 1) % len(all_groups)]
        students.append(
            {
                "student_id": student_id,
                "full_name": fake.name(),
                "faculty": faculty,
                "group_name": group_name,
                "year": int(group_name.split("-")[1][0]),
                "enrollment_date": (datetime.now() - timedelta(days=int(rng.integers(200, 1400)))).date().isoformat(),
                "email": fake.email(),
            }
        )
    students_df = pd.DataFrame(students)

    courses = []
    for course_id in range(1, 31):
        faculty = FACULTIES[(course_id - 1) % len(FACULTIES)]
        courses.append(
            {
                "course_id": course_id,
                "course_name": f"{faculty} Course {course_id:02d}",
                "faculty": faculty,
                "credits": int(rng.integers(3, 7)),
                "semester": int(rng.integers(1, 9)),
            }
        )
    courses_df = pd.DataFrame(courses)

    grades = pd.DataFrame(
        {
            "grade_id": np.arange(1, 5001),
            "student_id": rng.integers(1, 501, 5000),
            "course_id": rng.integers(1, 31, 5000),
            "grade": np.clip(rng.normal(74, 15, 5000), 0, 100).round(1),
            "exam_date": [d.date().isoformat() for d in _date_range(rng, 180, 5000)],
        }
    )
    # Intentional dirty rows for DQ/Silver demo.
    grades.loc[0, "grade"] = 130
    grades.loc[1, "student_id"] = np.nan

    assignments = pd.DataFrame(
        {
            "assignment_id": np.arange(1, 4001),
            "student_id": rng.integers(1, 501, 4000),
            "course_id": rng.integers(1, 31, 4000),
            "assigned_at": _date_range(rng, 150, 4000),
            "due_at": _date_range(rng, 120, 4000),
            "submitted": rng.choice([0, 1], 4000, p=[0.22, 0.78]),
            "score": np.clip(rng.normal(76, 18, 4000), 0, 100).round(1),
        }
    )
    assignments.loc[2, "score"] = -5

    lms_activity = pd.DataFrame(
        {
            "event_id": np.arange(1, 8001),
            "student_id": rng.integers(1, 501, 8000),
            "course_id": rng.integers(1, 31, 8000),
            "event_type": rng.choice(VALID_LMS_EVENT_TYPES, 8000, p=[0.25, 0.35, 0.2, 0.12, 0.08]),
            "event_ts": _date_range(rng, 120, 8000),
            "duration_minutes": rng.integers(1, 181, 8000),
        }
    )
    lms_activity.loc[3, "duration_minutes"] = 300

    submissions = assignments.loc[assignments["submitted"] == 1, ["assignment_id", "student_id", "course_id", "score"]].copy()
    submissions.insert(0, "submission_id", np.arange(1, len(submissions) + 1))
    submissions["submitted_at"] = _date_range(rng, 120, len(submissions))

    material_views = lms_activity.loc[lms_activity["event_type"] == "view_material", ["event_id", "student_id", "course_id", "event_ts", "duration_minutes"]].copy()
    material_views = material_views.rename(columns={"event_id": "view_id", "event_ts": "view_ts"})
    material_views["material_id"] = rng.integers(1, 301, len(material_views))

    buildings = pd.DataFrame(
        {
            "building_id": np.arange(1, 11),
            "building_name": [f"Campus Building {i}" for i in range(1, 11)],
            "campus_zone": rng.choice(["North", "South", "East", "West"], 10),
        }
    )
    rooms = pd.DataFrame(
        {
            "room_id": np.arange(1, 51),
            "building_id": rng.integers(1, 11, 50),
            "room_name": [f"Room {100 + i}" for i in range(1, 51)],
            "capacity": rng.integers(20, 151, 50),
            "room_type": rng.choice(["lecture", "lab", "seminar"], 50),
        }
    )
    rooms.loc[4, "capacity"] = 0
    room_events = pd.DataFrame(
        {
            "room_event_id": np.arange(1, 5001),
            "room_id": rng.integers(1, 51, 5000),
            "event_type": rng.choice(VALID_ROOM_EVENT_TYPES, 5000),
            "event_ts": _date_range(rng, 120, 5000),
            "occupancy": rng.integers(1, 160, 5000),
        }
    )

    return {
        "students": students_df,
        "courses": courses_df,
        "grades": grades,
        "assignments": assignments,
        "lms_activity": lms_activity,
        "submissions": submissions,
        "material_views": material_views,
        "buildings": buildings,
        "rooms": rooms,
        "room_events": room_events,
    }
