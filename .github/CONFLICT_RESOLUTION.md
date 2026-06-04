# Как убрать конфликт в Pull Request GitHub

GitHub показывает конфликт не потому, что в файлах есть строки `<<<<<<<`, `=======`, `>>>>>>>`. Эти маркеры в текущей версии отсутствуют и дополнительно проверяются тестом `test_conflicting_files_have_no_merge_markers`.

Причина конфликта: PR-ветка и `main` одновременно изменили одни и те же файлы:

- `DEMO_SCENARIO.md`
- `README.md`
- `dashboard/app.py`
- `src/data_quality.py`
- `src/semantic_layer.py`
- `tests/test_pipeline.py`

Чтобы GitHub перестал показывать блок **This branch has conflicts that must be resolved**, нужно создать merge commit в PR-ветке, подтянув `main` и оставив текущую русскоязычную demo-версию этих файлов.

## Вариант через командную строку

На локальной машине с доступом к GitHub выполните:

```bash
git clone https://github.com/karmazyanrobert-collab/project_robert.git
cd project_robert
git checkout codex/create-new-university-data-platform-demo

git fetch origin main
git merge origin/main

git checkout --ours DEMO_SCENARIO.md
git checkout --ours README.md
git checkout --ours dashboard/app.py
git checkout --ours src/data_quality.py
git checkout --ours src/semantic_layer.py
git checkout --ours tests/test_pipeline.py

git add DEMO_SCENARIO.md README.md dashboard/app.py src/data_quality.py src/semantic_layer.py tests/test_pipeline.py
git commit -m "Resolve PR conflicts keeping Russian demo version"
git push origin codex/create-new-university-data-platform-demo
```

После push страница Pull Request обновится, и GitHub должен убрать список конфликтующих файлов.

## Вариант через GitHub web editor

1. Нажмите **Resolve conflicts** в Pull Request.
2. Для каждого из 6 файлов оставьте текущую русскоязычную demo-версию из PR-ветки.
3. Удалите все conflict markers, если GitHub их вставит.
4. Нажмите **Mark as resolved** для каждого файла.
5. Нажмите **Commit merge**.

## Почему нужно оставлять текущую версию PR

Именно текущая версия содержит:

- автономный запуск dashboard через `dashboard/app.py`;
- русскоязычный интерфейс для защиты;
- раздел Lakehouse Bronze/Silver/Gold;
- понятное объяснение Data Quality FAIL;
- Feature Store preview;
- автоматические demo streaming events;
- тесты pipeline, semantic layer, streaming и отсутствия merge-маркеров.
