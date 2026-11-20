# API та контракти

Префікс основного API: `/api/v1`. Обмін JSON у UTF-8. Успішна операція вилучення синхронна: жодної черги/довготривалого завдання у ПР14 немає, бо підставний обробник і тонкий прототип повертають невеликий результат у межах одного запиту. Майбутній повільний провайдер може вимагати окремого ADR і фонового контракту.

## `GET /api/health`

200:

```json
{
  "status": "ok",
  "version": "dev",
  "provider": "mock",
  "model": "mock-syllabus-v1",
  "mode": "mock",
  "storage": "ok",
  "additional_component": "not_loaded",
  "uptime_s": 12.34
}
```

Не викликає LLM. Відповідь не містить конфігураційного ключа, тексту запиту чи персональних даних. Недоступне сховище повертає контрольовану помилку 503.

## `POST /api/v1/syllabi/parse`

Запит:

```json
{
  "source_text": "Course syllabus text ...",
  "case_id": null
}
```

`source_text`: непорожній рядок довжиною щонайбільше 100000 символів. `case_id`: необов'язковий ідентифікатор прикладу з `eval/cases.json`; призначений для локального прототипу/mock.

200:

```json
{
  "record_id": "UUID",
  "result": {
    "deadlines": [
      {"title": "Project submission", "due_date": "2026-12-10", "description": null}
    ],
    "topics": [
      {"title": "Learning topic", "description": null}
    ],
    "scores": [
      {"name": "Project", "points": 30, "max_points": 100}
    ]
  }
}
```

`due_date` — ISO `YYYY-MM-DD` або `null`, якщо дата не визначена; `points` та `max_points` — невід'ємні числа, максимальна оцінка додатна. Списки можуть бути порожніми. Текст джерела не включається до відповіді або запису.

## `GET /api/v1/syllabi/{record_id}`

200 повертає ту саму схему, що й POST. `record_id` — UUID. Відсутній запис — 404.

## Єдиний формат помилки

Кожна помилка API має вигляд:

```json
{"error":{"kind":"validation_error","message":"Request validation failed.","retryable":false,"request_id":"UUID"}}
```

| HTTP | `kind` | Коли застосовується | Повторювати |
|---|---|---|---|
| 400 | `validation_error` | Некоректне тіло або типи запиту. | Ні, виправити запит. |
| 404 | `not_found` | Маршрут або запис не знайдено. | Ні. |
| 409 | `conflict` | Конфлікт унікальності запису. | Після зміни запиту. |
| 422 | `invalid_output` | Вихід провайдера не відповідає схемі. | Залежить від причини; `false` за замовчуванням. |
| 429 | `rate_limit` | Провайдер обмежив частоту запитів. | Так. |
| 503 | `unavailable` / `not_implemented` | Сховище/провайдер недоступні або інтеграцію ще не реалізовано. | Так для недоступності. |
| 504 | `timeout` | Тайм-аут провайдера. | Так. |

Неочікувані серверні помилки повертаються як 503 `internal_error` без деталей винятку. У кожній відповіді `request_id` збігається з заголовком `X-Request-ID` та записами журналу. Секрети й внутрішні exception-повідомлення не повертаються.

## Контракт провайдера

`Provider.generate(ProviderRequest) -> ProviderResponse`. Запит має `request_id`, `source_text`, необов'язковий `case_id`, `model`; відповідь містить тільки рядок `output_json` і використану назву моделі. Gateway декодує JSON і перевіряє його за `SyllabusExtraction`. Провайдер не пише в сховище та не формує HTTP-відповідь. Помилки провайдера — типізовані (`timeout`, `rate_limit`, `unavailable`, `not_implemented`); пошкоджений вихід обробляється gateway як `invalid_output`.

## Структурований вихід основного сценарію

`SyllabusExtraction = {deadlines: Deadline[], topics: Topic[], scores: Score[]}`. `Deadline = {title: string, due_date: ISO date|null, description: string|null}`; `Topic = {title: string, description: string|null}`; `Score = {name: string, points: number >= 0, max_points: number > 0}`. Ця форма використовується провайдером, API та сховищем без окремих несумісних DTO.
