# БКМ — SEO, доступность и защита: 27 октября 2026

## Проверено на действующем сайте

Источник: GitHub Actions 40516067817, job 122230208124, 27.10.2026 13:53:32 UTC.
https://github.com/whatmine00001-eng/bkm-website/actions/runs/40516067817/job/122230208124

Проверка — обычные публичные GET-запросы с runner Azure eastus. Никаких запросов к приватным файлам, секретам, CRM, изменений сайта или DNS. Это не пентест и не проверка из всех стран.

- HTTPS главной страницы: 200, без отключения проверки сертификата.
- HTTP главной: 200 БЕЗ перенаправления на HTTPS.
- HTTPS www.24bkm.com: 200 БЕЗ перенаправления на 24bkm.com.
- HTTPS /index.html: 200; canonical на корень https://24bkm.com/ присутствует.
- robots.txt: 200; User-agent: *, Allow: /, ссылка на sitemap.
- sitemap.xml: 200; 14 адресов. Рабочая ветка имеет 16 страниц, но это не означает их публикацию на основном сайте.
- Главная не содержит robots noindex и X-Robots-Tag noindex в проверенном ответе.
- На главной отсутствуют JSON-LD Organization/WebSite, og:site_name, google-site-verification и yandex-verification. Отсутствие метатегов НЕ доказывает отсутствие подтверждения через DNS или файл.
- В проверенных ответах главной нет Strict-Transport-Security, Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy. Это недостающие защитные меры, а не доказательство взлома.
- Изображения главной зависят от images.unsplash.com. Нужна инвентаризация всех внешних ресурсов, включая CSS/шрифты, и перенос разрешённых к локальному размещению ресурсов.
- Запрос одного заведомо отсутствующего HTML-файла вернул корректный 404.

## Подготовлено, но НЕ опубликовано

scripts/prepare-seo-candidate.py создаёт отдельный _seo_candidate из безопасной _production_release. Он НЕ является частью текущего live workflow и ничего не отправляет на Beget.

Подготовленные изменения:
- заголовок главной: «БКМ (BKM) — импортные поставки, логистика и таможенное оформление»;
- заголовки услуг с БКМ (BKM), описания и Open Graph;
- Organization и WebSite с name БКМ, alternateName BKM/24BKM, исходным логотипом и подтверждёнными контактами;
- один canonical на страницу, проверка sitemap;
- referrer meta strict-origin-when-cross-origin;
- возможность добавить публичные коды подтверждения Google/Yandex из seo/search-verification.json; без кодов фиктивные значения не добавляются;
- тело HTML, исходный логотип, дизайн и слоганы сохраняются;
- приём данных остаётся выключенным; API и черновая политика в SEO-сборку не входят.

Отдельный workflow BKM SEO Candidate - Validate Only проверяет сборку, неизменность видимого HTML и запрет CRM; нет SSH, секретов или публикации. _seo_candidate нельзя загружать поверх живого сайта без отдельного решения о выпуске и сверки актуальных страниц.

## Следующие настройки хостинга — не применены

Единый адрес: https://24bkm.com/. Подготовить постоянные 301/308 перенаправления HTTP → HTTPS, www → без www, /index.html → /. Сохранять остальные пути и query/UTM. Не менять NS, MX, DNS Bitrix24 или настройки CRM.

Проверить применение защитных заголовков именно к статическим HTML nginx. Нельзя считать, что добавление .htaccess автоматически изменило заголовки nginx.

Базовые значения для согласования с Beget:

```text
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

CSP сначала в Report-Only после инвентаризации inline JS, стилей, шрифтов, картинок и будущей Метрики; строгая непроверенная политика может сломать сайт. Не включать широкое unsafe-inline для scripts ради зелёного отчёта. HSTS вводить поэтапно после проверки HTTPS; пока без includeSubDomains/preload, чтобы не затронуть CRM/тестовые поддомены.

Дополнительно: закрыть dotfiles, архивы и резервные копии на уровне сервера; приватный config.php оставить вне public_html. Применять 2FA/passkeys и уникальные пароли для Beget, GitHub, регистратора и административной почты; проверить права и историю доступа; резервные копии и реальное восстановление. Проверить защиту от DDoS у хостинга. WAF/CDN выбирать только после тестов доступности для клиентов; не блокировать всех иностранных посетителей или поисковых роботов.

## Поиск и доступность

Ни одна настройка не гарантирует первое место по BKM/БКМ или доступность из каждой сети мира. Начальная целевая семантика: БКМ логистика, BKM logistics, БКМ импорт, БКМ таможенное оформление, 24bkm. Для заявок также важны отдельные страницы услуг, маршрутов и полезные проверенные материалы, а не только новости.

Для диагностики реальной индексации нужны аккаунты владельца Google Search Console и Яндекс Вебмастер. Предпочтительный без изменения DNS вариант: URL-prefix property https://24bkm.com/ и HTML meta verification. Включение поисковой верификации даёт права на сайт — использовать только код, полученный владельцем в его аккаунте. Пароли и webhook не передавать.

Источники:
https://developers.google.com/search/docs/fundamentals/seo-starter-guide
https://developers.google.com/search/docs/appearance/site-names
https://developers.google.com/search/docs/appearance/structured-data/organization
https://yandex.ru/support/webmaster/ru/service/rights
https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
