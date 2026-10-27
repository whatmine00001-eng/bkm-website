# БКМ — проверка вебхука и готовности лидов

## Актуальный результат — 27 октября 2026, 12:46:57–12:46:58 UTC

После сообщения владельца «классический режим включен» повторно выполнена существующая проверка BKM Lead Readiness - Read Only. Запуск **40505218988**, новая задача **122196875546**, результат **success**.

Источник: https://github.com/whatmine00001-eng/bkm-website/actions/runs/40505218988/job/122196875546
Проверенная ревизия диагностического кода: 9327b5097ee8bb13f2f84dc7c8dfd62e51fa0fee.

| Проверка | Подтверждённый результат |
|---|---|
| Приватный config.php и соединение Beget → Bitrix24 | PASS; вебхук API доступен |
| Режим CRM | CLASSIC_WITH_LEADS — классическая CRM с лидами |
| Схема полей, нужных обработчику | LEAD_SCHEMA: PASS |
| Обязательные поля без гарантированного заполнения | REQUIRED_FIELDS_REVIEW: NONE по метаданным |
| Настроенная начальная стадия (по умолчанию NEW) | LEAD_STAGE: PASS |
| Источник WEB | SOURCE_WEB: PASS |
| Назначение ответственного | PORTAL_DEFAULT_NOT_VERIFIED — отдельный ID не настроен и назначение не проверено |
| enabled и privacy_approved | BOTH_FALSE; не изменялись |
| Итог проверки метаданных | READINESS_METADATA: PASS |

Точные строки результата:

```text
BKM CRM connection check PASSED: private config readable, webhook API available. Website form stays disabled.
LEAD_SCHEMA: PASS
REQUIRED_FIELDS_REVIEW: NONE
CRM_MODE: CLASSIC_WITH_LEADS
LEAD_STAGE: PASS
SOURCE_WEB: PASS
ASSIGNMENT: PORTAL_DEFAULT_NOT_VERIFIED
COLLECTION_FLAGS: BOTH_FALSE
NO_WRITES: no leads created; no contacts read; website and private settings unchanged.
NOT_VERIFIED: create permission, assignment validity, stage-specific requirements, robots, web PHP and end-to-end submission.
READINESS_METADATA: PASS
```

## Границы проверки

Выполнялись только crm.lead.fields, crm.settings.mode.get и crm.status.list. Лиды не создавались, существующие клиенты и контакты не читались, публичный сайт, DNS и приватная конфигурация не менялись. Скрипты выполнялись во временном закрытом каталоге Beget и удалены после проверки.

**Успешная проверка метаданных не равна готовности публичной формы.** Пока не проверены право создания лида, реальное назначение ответственного, дополнительные требования стадий, роботы/уведомления, PHP веб-сервера и сквозная отправка через браузер.

## Что требуется до публичного запуска

1. Подготовить и утвердить документы для формы. Повторная проверка каталога approved/ показала только README.md; approved/privacy.html отсутствует. Не публиковать черновик как утверждённую политику. Нужны подтверждённые реквизиты оператора сайта, описание обработки и согласование документа владельцем.
2. Определить сотрудника для обработки новых лидов и его ID в Bitrix24. Не назначать произвольный ID и не считать ID владельца вебхука автоматически выбранным менеджером.
3. Выполнить отдельно согласованный контролируемый тестовый лид и сквозную проверку формы/сервера/CRM. До этого не заявлять, что заявки уже принимаются.
4. Публиковать только проверенную сборку по согласованному плану; до готовности оставить enabled=false и privacy_approved=false.

## История

Ранее 27 октября формат URL вебхука и связь с Bitrix24 были проверены успешно: запуск 40501015778, job 122190265195, и запуск 39977984817, job 122190633991.

Первая попытка расширенной проверки 40505218988, job 122192682699, обнаружила SIMPLE_WITHOUT_LEADS и завершилась REVIEW_REQUIRED. Это историческое замечание **устранено**: новая задача 122196875546 подтвердила CLASSIC_WITH_LEADS. Вебхук повторно менять не требовалось.

Документация режима: https://apidocs.bitrix24.ru/api-reference/crm/crm-settings-mode-get.html
