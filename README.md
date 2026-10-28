<div align="center">

# feyegetsu.dev

**Сайты, Telegram-боты и Mini App для малого бизнеса**

[![CI](https://github.com/feyegetsu/portfolio/actions/workflows/ci.yml/badge.svg)](https://github.com/feyegetsu/portfolio/actions/workflows/ci.yml)
[![Assets](https://github.com/feyegetsu/portfolio/actions/workflows/screenshots.yml/badge.svg)](https://github.com/feyegetsu/portfolio/actions/workflows/screenshots.yml)
![HTML/CSS/JS](https://img.shields.io/badge/stack-HTML%20·%20CSS%20·%20JS%20·%20Python-7c5cff)
![No frameworks](https://img.shields.io/badge/фреймворки-0-22d3ee)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

### [Открыть портфолио →](https://feyegetsu.github.io/portfolio/)

<img src="assets/hero.jpg" alt="Главная страница портфолио" width="100%">

</div>

## Что внутри

**10 живых проектов** для разных ниш. Каждый можно потрогать: оформить заказ, записаться, посчитать ипотеку. На главной у каждого проекта есть кейс с задачей, решением, техническими деталями и интерактивным превью в рамке компьютера или телефона.

| | Проект | Ниша | Ключевая фишка |
|---|---|---|---|
| <img src="assets/previews/miniapp.jpg" width="160"> | [**Сытый Лис**](https://feyegetsu.github.io/portfolio/projects/miniapp/) | Telegram Mini App | Доставка еды внутри Telegram: тема, MainButton, вибрация, статус заказа |
| <img src="assets/previews/florist.jpg" width="160"> | [**Пион & Ко**](https://feyegetsu.github.io/portfolio/projects/florist/) | Интернет-магазин | Каталог с фильтрами, корзина с сохранением, доставка по интервалам |
| <img src="assets/previews/dental.jpg" width="160"> | [**Белая линия**](https://feyegetsu.github.io/portfolio/projects/dental/) | Медицина | Квиз, который считает стоимость лечения |
| <img src="assets/previews/realty.jpg" width="160"> | [**Квадрат**](https://feyegetsu.github.io/portfolio/projects/realty/) | Недвижимость | Фильтры, избранное, галерея объекта, ипотечный калькулятор |
| <img src="assets/previews/saas.jpg" width="160"> | [**Taskly**](https://feyegetsu.github.io/portfolio/projects/saas/) | IT-стартап | Канбан с drag & drop мышью и пальцем, расчёт тарифа |
| <img src="assets/previews/autoservice.jpg" width="160"> | [**МоторЛайн**](https://feyegetsu.github.io/portfolio/projects/autoservice/) | Авто | Калькулятор ремонта, отслеживание статуса машины |
| <img src="assets/previews/fitness.jpg" width="160"> | [**PULSE**](https://feyegetsu.github.io/portfolio/projects/fitness/) | Спорт | Расписание на неделю с записью и свободными местами |
| <img src="assets/previews/barbershop.jpg" width="160"> | [**BLADE**](https://feyegetsu.github.io/portfolio/projects/barbershop/) | Красота | Онлайн-запись в 3 шага со свободными слотами |
| <img src="assets/previews/cafe.jpg" width="160"> | [**Зерно**](https://feyegetsu.github.io/portfolio/projects/cafe/) | Общепит | Меню с фото, галерея, бронь столика |
| 🤖 | [**Бот для заказов**](projects/cafe-bot/) | Telegram-бот | Python + aiogram 3: корзина, заказы в SQLite, уведомления админу, рассылки |

<div align="center">
<img src="assets/previews/miniapp-mobile.jpg" width="30%" alt="Mini App на телефоне">
<img src="assets/previews/florist-mobile.jpg" width="30%" alt="Магазин цветов на телефоне">
<img src="assets/previews/realty-mobile.jpg" width="30%" alt="Каталог недвижимости на телефоне">
</div>

### Кейсы

У каждого проекта есть кейс: задача бизнеса, что сделано, как устроено внутри, и живое превью, которое можно переключать между компьютером и телефоном. На кейс можно дать прямую ссылку, например [#case-miniapp](https://feyegetsu.github.io/portfolio/#case-miniapp).

<img src="assets/case.jpg" alt="Кейс проекта с живым превью" width="100%">

## Качество, которое можно проверить

Цифры не написаны руками: их считает Lighthouse в GitHub Actions при каждом изменении сайта и кладёт в [`assets/lighthouse.json`](assets/lighthouse.json).

<!-- LIGHTHOUSE:START -->
Замер от 2026-10-28. Страницы без пометки измерены в мобильном режиме (медленный 4G, слабый процессор).

| Страница | Скорость | Доступность | Практики | SEO | LCP |
|---|---|---|---|---|---|
| Главная (телефон) | 🟢 98 | 🟢 96 | 🟢 100 | 🟢 100 | 2.1 s |
| Главная (компьютер) | 🟢 98 | 🟢 96 | 🟢 100 | 🟢 100 | 1.1 s |
| Mini App | 🟢 92 | 🟢 100 | 🟢 100 | 🟢 100 | 2.6 s |
| Пион & Ко | 🟢 99 | 🟢 100 | 🟢 100 | 🟢 100 | 1.5 s |
| Белая линия | 🟢 100 | 🟢 100 | 🟢 100 | 🟢 100 | 0.9 s |
| Зерно | 🟢 94 | 🟢 100 | 🟢 100 | 🟢 100 | 3.0 s |
| BLADE | 🟠 80 | 🟢 100 | 🟢 100 | 🟢 100 | 4.0 s |
| PULSE | 🟠 85 | 🟢 100 | 🟢 100 | 🟢 100 | 2.5 s |
| МоторЛайн | 🟢 96 | 🟢 100 | 🟢 100 | 🟢 100 | 2.5 s |
| Квадрат | 🟢 99 | 🟢 100 | 🟢 100 | 🟢 100 | 1.9 s |
| Taskly | 🟢 100 | 🟢 100 | 🟢 100 | 🟢 100 | 0.9 s |
<!-- LIGHTHOUSE:END -->

- **CI на каждый пуш.** Бот проходит линтер `ruff` и проверку импорта, все HTML-страницы проверяются на битые ссылки.
- **Скриншоты обновляются сами.** Playwright снимает каждый проект и OG-картинку и коммитит их в `assets/`.
- **Доступность.** Семантическая разметка, фокус с клавиатуры, модальные окна на `<dialog>`, учёт `prefers-reduced-motion`.
- **SEO.** Мета-теги, Open Graph, JSON-LD `ProfessionalService`, `sitemap.xml`, `robots.txt`, canonical.

## Как устроено

```
index.html, styles.css, script.js   главная: кейсы, калькулятор стоимости, симуляция бота
projects/
  miniapp/                          Telegram Mini App (Telegram WebApp API)
  florist/ dental/ realty/ saas/
  autoservice/ fitness/ barbershop/ cafe/
  shared/motion.js                  анимации через data-атрибуты: появление, параллакс, счётчики
  cafe-bot/                         Telegram-бот на Python (aiogram 3, SQLite)
tools/
  screenshots.py                    скриншоты и OG-картинка (Playwright)
  lh_summary.py                     сводка отчётов Lighthouse
.github/workflows/
  ci.yml                            линтер бота и проверка ссылок
  screenshots.yml                   скриншоты и Lighthouse с автокоммитом
```

**Почему без фреймворков.** Для сайтов малого бизнеса важнее всего скорость загрузки с мобильного и простота поддержки. Чистые HTML, CSS и JS открываются с любого хостинга, не требуют сборки, а каждый демо-проект — один файл, который легко взять за основу под реального клиента.

## Запуск локально

```bash
git clone https://github.com/feyegetsu/portfolio.git
cd portfolio
python -m http.server 8000
```

Откройте http://localhost:8000. Контакты на главной задаются в одном месте: объект `CONFIG` в начале [`script.js`](script.js).

Бот запускается отдельно, инструкция в [`projects/cafe-bot/README.md`](projects/cafe-bot/README.md).

## Лицензия

Код распространяется по лицензии [MIT](LICENSE). Фото загружаются с [Unsplash](https://unsplash.com/license), шрифты с Google Fonts. Компании, люди, отзывы и цифры в демо-проектах вымышлены.
