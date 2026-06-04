from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src.config import VALID_STREAMING_EVENT_TYPES
from src.warehouse import get_connection


def generate_streaming_events(n_events: int = 80) -> int:
    rng = np.random.default_rng()
    with get_connection() as con:
        students = con.execute("SELECT student_id, faculty, group_name FROM student_performance_gold").fetchdf()
        max_id = con.execute("SELECT COALESCE(MAX(event_id), 0) FROM streaming_events").fetchone()[0]
        sample = students.sample(n=n_events, replace=True, random_state=int(rng.integers(0, 1_000_000))).reset_index(drop=True)
        now = datetime.now().replace(microsecond=0)
        events = sample.copy()
        events.insert(0, "event_id", np.arange(max_id + 1, max_id + n_events + 1))
        events.insert(1, "event_ts", [now - timedelta(seconds=int(x)) for x in rng.integers(0, 600, n_events)])
        events["event_type"] = rng.choice(VALID_STREAMING_EVENT_TYPES, n_events, p=[0.55, 0.25, 0.20])
        events["payload"] = events["event_type"].map(lambda e: f"demo_event={e}")
        con.register("new_events", events)
        con.execute("INSERT INTO streaming_events SELECT * FROM new_events")
        con.unregister("new_events")
        metrics = con.execute(
            """
            SELECT NOW()::TIMESTAMP AS metric_ts,
                   COUNT(*) / 10.0 AS events_per_minute,
                   COUNT(DISTINCT student_id) FILTER (WHERE event_ts >= NOW() - INTERVAL 5 MINUTE) AS active_students_last_5m,
                   COUNT(*) FILTER (WHERE event_type = 'assignment_submission' AND event_ts >= NOW() - INTERVAL 5 MINUTE) AS assignment_submissions_last_5m,
                   COUNT(*) FILTER (WHERE event_type = 'building_entry' AND event_ts >= NOW() - INTERVAL 5 MINUTE) AS building_entries_last_5m
            FROM streaming_events
            WHERE event_ts >= NOW() - INTERVAL 10 MINUTE
            """
        ).fetchdf()
        con.register("new_metrics", metrics)
        con.execute("INSERT INTO streaming_metrics SELECT * FROM new_metrics")
        con.unregister("new_metrics")
    return n_events
