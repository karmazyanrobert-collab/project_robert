# DEMO_SCENARIO: сценарий защиты

## 1. Открыть dashboard

Откройте приложение Streamlit Cloud с entrypoint `dashboard/app.py`. При первом запуске dashboard проверяет наличие `data/warehouse.duckdb`. Если файла нет, он автоматически запускает pipeline, генерирует данные и строит хранилище.

## 2. Показать архитектуру

Покажите текстовую схему на странице:

```text
Source systems → Bronze → Data Quality → Silver → Gold → Feature Store → Semantic Layer → Dashboard
```

Объясните, что это компактная локальная версия enterprise data platform.

## 3. Показать генерацию pipeline

Нажмите **Run / Regenerate pipeline**. Pipeline выполняет полный цикл:

- генерация synthetic source data;
- сохранение raw parquet в Bronze;
- запуск Data Quality;
- очистка данных в Silver;
- построение Gold mart tables;
- загрузка DuckDB warehouse.

## 4. Показать Bronze/Silver/Gold

Внизу Data Quality section dashboard показывает пути слоёв:

- `data/bronze` — сырые данные как есть;
- `data/silver` — очищенные данные без дублей, null и некорректных значений;
- `data/gold` — аналитические витрины.

Gold-таблицы: `student_performance_gold`, `faculty_performance_gold`, `group_performance_gold`, `lms_engagement_gold`, `room_utilization_gold`, `student_features`.

## 5. Показать Data Quality

Откройте таблицу **Data Quality Report**. В ней есть:

- check name;
- table name;
- status;
- failed rows;
- message.

Объясните проверки: `student_id not null`, `student_id unique`, диапазоны оценок, длительность LMS, вместимость аудиторий и валидные типы событий.

## 6. Показать Feature Store

Откройте **Feature Store Preview**. Объясните признаки:

- `avg_grade`;
- `completion_rate`;
- `engagement_score`;
- `attendance_score`;
- `risk_flag`.

`risk_flag = 1`, если средняя оценка ниже 60, completion rate ниже 0.6 или engagement score находится в низком сегменте.

## 7. Показать фильтры Faculty/Group

В sidebar выберите Faculty. Dashboard перейдёт с faculty-level на group-level аналитику. Затем выберите Group — dashboard покажет student-level drill-down. KPI, графики и таблицы изменяются согласно фильтрам.

## 8. Показать Streaming Analytics

Нажмите **Generate streaming events**. Это локальная cloud-friendly замена Kafka:

- события записываются в таблицу `streaming_events` в DuckDB;
- агрегаты пишутся в `streaming_metrics`;
- dashboard показывает последние 20 событий, events per minute, active students last 5 minutes, assignment submissions last 5 minutes и building entries last 5 minutes.

## 9. Показать Risk Students

Откройте таблицу **Risk students**. Это пример аналитического продукта для деканата или student success team: можно быстро найти студентов с риском академических проблем.

## 10. Объяснить локальные аналоги enterprise-инструментов

- Airflow заменён на `pipeline.py`.
- Kafka заменена на `streaming_demo.py`.
- ClickHouse заменён на DuckDB.
- Grafana заменена на Streamlit.
- S3/MinIO заменены локальными папками `data/bronze`, `data/silver`, `data/gold`.
- Feast заменён таблицей `student_features`.
- Cube.js заменён `semantic_layer.py`.
