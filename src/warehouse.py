from __future__ import annotations

import duckdb
import pandas as pd

from src.config import WAREHOUSE_PATH, ensure_directories


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    ensure_directories()
    return duckdb.connect(str(WAREHOUSE_PATH), read_only=read_only)


def load_gold_tables(gold_tables: dict[str, pd.DataFrame], dq_report: pd.DataFrame) -> None:
    ensure_directories()
    with get_connection() as con:
        for table_name, df in gold_tables.items():
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            con.register("tmp_df", df)
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
        con.execute("DROP TABLE IF EXISTS data_quality_report")
        con.register("dq_df", dq_report)
        con.execute("CREATE TABLE data_quality_report AS SELECT * FROM dq_df")
        con.unregister("dq_df")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS streaming_events (
                event_id BIGINT,
                event_ts TIMESTAMP,
                student_id BIGINT,
                faculty VARCHAR,
                group_name VARCHAR,
                event_type VARCHAR,
                payload VARCHAR
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS streaming_metrics (
                metric_ts TIMESTAMP,
                events_per_minute DOUBLE,
                active_students_last_5m BIGINT,
                assignment_submissions_last_5m BIGINT,
                building_entries_last_5m BIGINT
            )
            """
        )
