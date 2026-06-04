# University Data Platform Demo

Полностью автономная демонстрационная Data Platform для университета. Проект создан с нуля для запуска в Streamlit Cloud без Docker, внешних API и платных сервисов.

## Что реализовано

- **Dashboard:** `dashboard/app.py` автоматически проверяет `data/warehouse.duckdb` и при первом запуске сам запускает pipeline.
- **Source systems:** генерируются домены `academic_performance`, `student_engagement`, `campus_infrastructure`.
- **Bronze/Silver/Gold:** данные сохраняются в `data/bronze`, `data/silver`, `data/gold` в parquet.
- **Data Quality:** проверки ключей, диапазонов оценок, длительности, вместимости аудиторий и допустимых event type.
- **DuckDB warehouse:** Gold-таблицы и DQ report загружаются в `data/warehouse.duckdb`.
- **Feature Store:** таблица `student_features` с признаками и `risk_flag`.
- **Semantic Layer:** функции в `src/semantic_layer.py` возвращают KPI, метрики, таблицы и streaming-аналитику.
- **Streaming Demo:** локальная замена Kafka — кнопка генерирует события и пишет их в DuckDB.

## Какие enterprise-инструменты заменены

| Enterprise tool | Локальный аналог в проекте |
|---|---|
| Airflow | `src/pipeline.py` |
| Kafka | `src/streaming_demo.py` |
| ClickHouse | DuckDB |
| Grafana | Streamlit dashboard |
| S3 / MinIO | `data/bronze`, `data/silver`, `data/gold` |
| Feast | `student_features` |
| Cube.js | `src/semantic_layer.py` |

## Как запустить в Streamlit Cloud

1. Загрузите репозиторий в GitHub.
2. В Streamlit Cloud создайте новое приложение.
3. Укажите entrypoint: `dashboard/app.py`.
4. Укажите `requirements.txt` как файл зависимостей.
5. Откройте ссылку приложения. Если warehouse ещё нет, dashboard автоматически создаст данные, Bronze/Silver/Gold и DuckDB.

## Как запустить локально

```bash
python -m pip install -r requirements.txt
streamlit run dashboard/app.py
```

Для проверки тестов:

```bash
python -m pytest tests -v
```

## Что показывать на защите

1. Открыть dashboard и показать, что он запускается без локальных команд.
2. Нажать **Run / Regenerate pipeline** и объяснить автоматическое построение Bronze/Silver/Gold.
3. Показать KPI, графики и таблицы.
4. Переключить Faculty и Group — метрики должны заметно измениться.
5. Изменить Date range — LMS и streaming-аналитика фильтруются по времени.
6. Показать Data Quality report.
7. Показать Feature Store Preview и объяснить `risk_flag`.
8. Нажать **Generate streaming events** и показать Last streaming events и метрики последних 5 минут.
9. Показать Risk Students как пример аналитического продукта для университета.
