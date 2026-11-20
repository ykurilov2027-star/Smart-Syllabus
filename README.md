# Smart Syllabus / Конспект-Трекер

Локальний walking skeleton для прототипування розбору силабуса у дедлайни, теми та бали. За замовчуванням застосунок використовує детермінований `mock` і не звертається до платного або реального AI API. Gemini-compatible провайдер у ПР14 — контрольована заглушка.

## Запуск у Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Відкрийте `http://127.0.0.1:8000/`. Перевірка стану доступна за `http://127.0.0.1:8000/api/health`.
Тестовий приклад для форми: `intro-course` або `project-course`.

Для роботи із заглушкою ключ не потрібен. Для наступного етапу можна налаштувати `LLM_PROVIDER=gemini_compat` і `LLM_API_KEY` або `GEMINI_API_KEY` у локальному `.env`; цей провайдер поки поверне `not_implemented`. Не додавайте `.env` чи секрети до репозиторію.

## API та розробка

- `POST /api/v1/syllabi/parse` — синхронне вилучення за контрактом у [docs/api.md](./docs/api.md).
- `GET /api/v1/syllabi/{record_id}` — читання збереженого структурованого результату.
- `GET /api/health` — health без виклику моделі та без розкриття секретів.
- SQLite і журнал налаштовуються через `DB_PATH` та `LOG_FILE`.
- `python -m pytest` — тести використовують виключно mock і тимчасові SQLite-файли.

Архітектурні межі та етапи описано в [docs/architecture.md](./docs/architecture.md), ADR — у [docs/adr/](./docs/adr/), робочий backlog — у [docs/backlog.md](./docs/backlog.md).
