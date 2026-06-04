from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
WAREHOUSE_PATH = DATA_DIR / "warehouse.duckdb"

FACULTIES = [
    "Computer Science",
    "Economics",
    "Engineering",
    "Medicine",
    "Humanities",
]
GROUPS_BY_FACULTY = {
    faculty: [f"{faculty[:3].upper()}-{year}{idx}" for year in (1, 2, 3, 4) for idx in range(1, 4)]
    for faculty in FACULTIES
}
VALID_LMS_EVENT_TYPES = ["login", "view_material", "submit_assignment", "quiz_attempt", "forum_post"]
VALID_ROOM_EVENT_TYPES = ["entry", "exit", "class_start", "class_end"]
VALID_STREAMING_EVENT_TYPES = ["lms_click", "assignment_submission", "building_entry"]
RANDOM_SEED = 42


def ensure_directories() -> None:
    for path in (DATA_DIR, BRONZE_DIR, SILVER_DIR, GOLD_DIR):
        path.mkdir(parents=True, exist_ok=True)
