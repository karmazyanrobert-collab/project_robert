# University Data Platform Demo

## 1. Название проекта

**University Data Platform Demo** — автономная демонстрационная Data Platform для университета с русскоязычным dashboard для защиты.

## 2. Цель проекта

Показать полный путь данных от университетских источников до аналитического dashboard без Docker, внешних API и платных сервисов. После деплоя в Streamlit Cloud пользователь открывает `dashboard/app.py`, а приложение само генерирует данные, строит Bronze/Silver/Gold, создаёт DuckDB warehouse и показывает аналитику.

## 3. Какие части задания закрывает проект

- Генерация данных по трём доменам: academic performance, student engagement, campus infrastructure.
- Bronze/Silver/Gold lakehouse-слои в parquet.
- Data Quality framework с отчётом PASS/FAIL и русскими пояснениями.
- DuckDB warehouse с Gold-витринами.
- Feature Store как таблица `student_features`.
- Semantic Layer на Python.
- Streaming demo без Kafka — через генератор событий и таблицы DuckDB.
- Streamlit dashboard на русском языке с KPI, фильтрами, графиками, таблицами и сценарием защиты.

## 4. Архитектура

```text
Источники данных
→ Bronze-слой
→ Проверка качества данных
→ Silver-слой
→ Gold-слой
→ Feature Store
→ DuckDB Warehouse
→ Semantic Layer
→ Streamlit Dashboard
```

Проект является демонстрационной автономной версией. В промышленном варианте локальные компоненты можно заменить на S3, Airflow, Kafka, ClickHouse, Grafana, Feast, Cube.js и Delta Lake/Iceberg.

## 5. Стек технологий

- Python
- pandas
- numpy
- duckdb
- pyarrow
- streamlit
- plotly
- faker
- pytest

## 6. Как запустить в Streamlit Cloud

1. Загрузить репозиторий в GitHub.
2. В Streamlit Cloud создать новое приложение.
3. Указать entrypoint: `dashboard/app.py`.
4. Указать зависимости из `requirements.txt`.
5. Открыть ссылку приложения. Если `data/warehouse.duckdb` отсутствует, dashboard автоматически запустит pipeline и подготовит все данные.

Ручной запуск команд для демонстрации в Streamlit Cloud не нужен.

## 7. Как запустить локально

```bash
python -m pip install -r requirements.txt
streamlit run dashboard/app.py
```

Тесты:

```bash
python -m pytest tests -v
```

## 8. Описание Lakehouse

Lakehouse реализован через локальные parquet-слои:

- `data/bronze` — сырые данные из источников как есть.
- `data/silver` — очищенные и типизированные данные.
- `data/gold` — аналитические витрины для отчётности, dashboard и ML-признаков.
- `data/warehouse.duckdb` — локальный аналитический warehouse.

Apache Iceberg и Delta Lake не используются специально, чтобы сохранить автономный запуск в Streamlit Cloud. В промышленной версии эти слои могут быть перенесены на S3 + Iceberg/Delta Lake для ACID-транзакций, time travel и управления метаданными.

## 9. Описание Data Quality

В Bronze специально добавлены несколько некорректных строк: неправильные оценки, нереалистичная длительность LMS-сессии и аудитория с нулевой вместимостью. Это нужно, чтобы на защите показать работу проверок качества.

Data Quality Report показывает:

- название проверки;
- таблицу;
- статус;
- количество ошибочных строк;
- русское пояснение.

После проверок Silver-слой очищает некорректные записи.

## 10. Описание Feature Store

Feature Store реализован как таблица `student_features` в DuckDB и parquet. В ней есть признаки:

- `student_id`;
- `avg_grade`;
- `completion_rate`;
- `engagement_score`;
- `attendance_score`;
- `risk_flag`.

`risk_flag = 1`, если средний балл ниже 60, доля выполненных заданий ниже 0.6 или индекс вовлечённости находится в низком сегменте. В промышленной версии этот компонент можно заменить на Feast.

## 11. Описание Streaming

Kafka заменена встроенным генератором потоковых событий. Кнопка **Сгенерировать потоковые события** добавляет события в DuckDB table `streaming_events`, а агрегаты записываются в `streaming_metrics`.

Dashboard показывает:

- событий за минуту;
- активных студентов за последние 5 минут;
- отправленные задания за последние 5 минут;
- входы в корпуса за последние 5 минут;
- последние 20 событий.

## 12. Ограничения демонстрационной версии

- Нет Docker и оркестрации контейнеров.
- Нет настоящих Kafka, Airflow, Grafana, ClickHouse, Feast, Cube.js.
- Нет настоящего S3/object storage.
- Нет Delta Lake/Iceberg transaction log.
- Данные синтетические и генерируются локально.

Эти ограничения сделаны осознанно: проект должен запускаться в Streamlit Cloud одной ссылкой и не требовать внешних сервисов.

## 13. Что заменено локальными аналогами

| Компонент задания | Реализация в демо |
|---|---|
| Object Storage / S3 | локальная структура `data/` |
| Airflow / Prefect | встроенный Python pipeline `src/pipeline.py` |
| Kafka | генератор событий `src/streaming_demo.py` |
| ClickHouse | DuckDB |
| Grafana | Streamlit dashboard |
| Feast | таблица `student_features` |
| Cube.js | Python semantic layer `src/semantic_layer.py` |
| Lakehouse | Bronze/Silver/Gold Parquet + DuckDB |
| Great Expectations | собственный Data Quality framework |

## 14. Проверка перед защитой

Перед финальной демонстрацией полезно выполнить минимальные проверки:

```bash
python -m py_compile dashboard/app.py src/*.py tests/test_pipeline.py
python -m pytest tests -v
```

В тестах также проверяется, что в ранее конфликтующих файлах нет стандартных merge-маркеров Git, поэтому репозиторий готов к открытию PR и деплою в Streamlit Cloud.
