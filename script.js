// ================= НАСТРОЙКИ: контакты меняются только здесь =================
const CONFIG = {
  telegram: "your_username",       // ник в Telegram без @
  email: "your@email.com",
  github: "feyegetsu",
  repo: "https://github.com/feyegetsu/portfolio",
};

const $ = (id) => document.getElementById(id);

// ---------- Контакты ----------
document.querySelectorAll("[data-contact]").forEach((el) => {
  const type = el.dataset.contact;
  if (type === "telegram") el.href = `https://t.me/${CONFIG.telegram}`;
  if (type === "github") el.href = `https://github.com/${CONFIG.github}`;
  if (type === "email") el.textContent = CONFIG.email;
});
document.querySelectorAll("[data-repo-link]").forEach((el) => {
  el.href = `${CONFIG.repo}/tree/main/${el.dataset.repoLink}`;
  el.target = "_blank";
  el.rel = "noopener";
});
$("year").textContent = new Date().getFullYear();

// ---------- Мобильное меню ----------
const burger = $("burger");
const nav = $("nav");
const setMenu = (open) => {
  nav.classList.toggle("open", open);
  burger.classList.toggle("open", open);
  burger.setAttribute("aria-expanded", open);
};
burger.addEventListener("click", () => setMenu(!nav.classList.contains("open")));
nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setMenu(false)));

// ---------- Бегущая строка ниш ----------
const niches = ["Кофейни", "Доставка еды", "Рестораны","Барбершопы", "Салоны красоты", "Клиники", "Фитнес", "Автосервисы", "Цветы", "Недвижимость", "Стартапы"];
$("ticker").innerHTML = [...niches, ...niches].map((n) => `<span>${n}</span>`).join("");

// ---------- Работы и кейсы ----------
// goal — задача бизнеса, done — что сделано, tech — как устроено внутри
const projects = [
  { slug: "miniapp", title: "Сытый Лис", niche: "Telegram Mini App", cat: "tg", isNew: true, phone: true,
    text: "Доставка еды внутри Telegram: меню, размеры пиццы, промокод, оформление и статус заказа.",
    tags: ["Mini App", "Telegram WebApp API", "Тема Telegram"],
    goal: "Ресторану доставки нужен канал заказов без комиссии агрегаторов и без разработки мобильного приложения.",
    done: ["Меню с поиском и «липкими» категориями, которые подсвечиваются при прокрутке", "Шторка товара: размер пиццы и добавки с пересчётом цены", "Корзина, доставка или самовывоз, промокод, бесплатная доставка от суммы", "Оформление с автоподстановкой имени из Telegram и живой статус заказа"],
    tech: ["Цвета берутся из темы Telegram через CSS-переменные SDK, поэтому приложение выглядит родным в светлой и тёмной теме", "Нативные MainButton, BackButton и вибрация; в обычном браузере их заменяют свои элементы", "Всё на чистом JS, без сборки: открывается мгновенно даже на слабом интернете"] },
  { slug: "florist", title: "Пион & Ко", niche: "Интернет-магазин", cat: "shop",
    text: "Магазин цветов: каталог с фильтрами, корзина с сохранением, оформление доставки.",
    tags: ["Корзина", "Фильтры", "localStorage"],
    goal: "Цветочной мастерской нужен магазин, где букет можно выбрать и оформить с телефона за минуту.",
    done: ["Каталог с фильтром по категориям и сортировкой по цене и популярности", "Выезжающая корзина с изменением количества и подсказкой до бесплатной доставки", "Оформление: адрес, дата и интервал доставки", "Подписка на цветы и быстрая кнопка «В корзину» на фото"],
    tech: ["Корзина хранится в localStorage и переживает перезагрузку; без него страница тоже работает", "Закрытие корзины по Esc и по клику на фон, блокировка прокрутки под ней", "Анимации отключаются при системной настройке «уменьшить движение»"] },
  { slug: "dental", title: "Стоматология «Белая линия»", niche: "Медицина", cat: "services",
    text: "Клиника с прайсом по вкладкам и квизом, который считает стоимость лечения.",
    tags: ["Квиз", "Прайс", "Лиды"],
    goal: "Клинике нужно снять страх «сколько это будет стоить» и получать больше заявок на первичную консультацию.",
    done: ["Квиз из трёх вопросов с расчётом примерной стоимости и закреплением скидки", "Прайс по направлениям, переключается без перезагрузки", "Карточки врачей, фото клиники и форма записи к конкретному врачу"],
    tech: ["Квиз — маленький конечный автомат: шаги и итог считаются из данных, вопросы легко менять", "Обязательная медицинская оговорка в подвале", "Счётчики и появление блоков из общего модуля анимаций"] },
  { slug: "cafe", title: "Кофейня «Зерно»", niche: "Общепит", cat: "food",
    text: "Сайт кофейни с меню по категориям, галереей и бронью столика.",
    tags: ["Меню", "Бронь", "Параллакс"],
    goal: "Кофейне нужен сайт, который передаёт атмосферу и превращает просмотр меню в визит.",
    done: ["Первый экран с интерьером на весь экран и параллаксом", "Меню с фото, переключение категорий без перезагрузки", "Галерея атмосферы и форма брони с выбором даты, времени и числа гостей"],
    tech: ["Нельзя выбрать прошедшую дату брони", "Фото подгружаются лениво и в нужном размере", "Шапка становится плотной при прокрутке"] },
  { slug: "barbershop", title: "Барбершоп BLADE", niche: "Красота", cat: "services",
    text: "Онлайн-запись в 3 шага: услуга, мастер, свободное время.",
    tags: ["Онлайн-запись", "Слоты"],
    goal: "Барбершопу нужно разгрузить администратора: клиенты должны записываться сами, в любое время.",
    done: ["Запись в три шага с прогресс-баром и сводкой перед подтверждением", "Календарь на неделю, занятые и прошедшие слоты недоступны", "Галерея работ и карточки мастеров"],
    tech: ["Сегодняшние слоты, которые уже прошли, блокируются по текущему времени", "Занятость слотов стабильна для каждого дня и не прыгает при переключении", "Чёрно-белые фото становятся цветными при наведении"] },
  { slug: "fitness", title: "Фитнес-клуб PULSE", niche: "Спорт", cat: "services",
    text: "Расписание на неделю с записью на занятия и абонементы с переключением периода.",
    tags: ["Расписание", "Тарифы"],
    goal: "Клубу нужно, чтобы клиенты сами записывались на групповые занятия и видели свободные места.",
    done: ["Расписание на 7 дней с фильтром по типу тренировок", "Запись и отмена в один клик, счётчик свободных мест", "Направления с фото и тарифы с переключением «месяц / год»"],
    tech: ["Расписание и заполненность генерируются из данных для каждого дня", "Пустой результат фильтра показывает подсказку, а не пустоту", "Живой счётчик «сейчас в клубе»"] },
  { slug: "autoservice", title: "Автосервис «МоторЛайн»", niche: "Авто", cat: "services",
    text: "Калькулятор стоимости ремонта и отслеживание статуса машины по номеру заказа.",
    tags: ["Калькулятор", "Статус заказа"],
    goal: "Автосервису нужно вызвать доверие: честная цена до визита и прозрачный ремонт.",
    done: ["Калькулятор: тип машины меняет коэффициент, итог и время работ считаются сразу", "Запись на ремонт прямо из калькулятора", "«Где моя машина?»: этапы ремонта по номеру заказа"],
    tech: ["Итог плавно «набегает», но всегда приходит к точной сумме, даже в фоновой вкладке", "Номер заказа экранируется перед выводом на страницу", "Иконки нарисованы SVG, без шрифтов-иконок"] },
  { slug: "realty", title: "Агентство «Квадрат»", niche: "Недвижимость", cat: "shop",
    text: "Каталог квартир с фильтрами и избранным, карточка объекта с галереей, ипотечный калькулятор.",
    tags: ["Каталог", "Ипотека", "Галерея"],
    goal: "Агентству нужен каталог, где клиент быстро сужает выбор и сразу понимает платёж по ипотеке.",
    done: ["Фильтры по комнатам, цене, типу и району, избранное", "Карточка объекта с галереей и платежом по ипотеке", "Ипотечный калькулятор с программами и долей переплаты"],
    tech: ["Аннуитетный платёж по формуле банка, переплата на круговой диаграмме", "Избранное сохраняется между визитами", "Карточки открываются и с клавиатуры, модалка закрывается по Esc"] },
  { slug: "saas", title: "Taskly", niche: "IT-стартап", cat: "startup",
    text: "Лендинг SaaS-сервиса с интерактивной канбан-доской и расчётом тарифа по числу людей.",
    tags: ["Drag & Drop", "Тарифы"],
    goal: "Стартапу нужно показать продукт в действии прямо на лендинге и довести до регистрации.",
    done: ["Канбан-доска на первом экране: карточки перетаскиваются между колонками", "Тарифы с ползунком числа участников и скидкой за год", "Bento-сетка возможностей, отзывы и FAQ"],
    tech: ["Перетаскивание работает и мышью (HTML5 DnD), и пальцем (свои touch-события)", "Конфетти при переносе задачи в «Готово»", "Карточки вставляются по позиции курсора, а не только в конец"] },
  { slug: "cafe-bot", title: "Бот для заказов", niche: "Telegram-бот", cat: "tg", bot: true,
    text: "Бот кафе на aiogram 3: меню, корзина, заказы в SQLite, уведомления админу, рассылки.",
    tags: ["Python", "aiogram 3", "SQLite"],
    goal: "Кафе нужно принимать заказы в Telegram и мгновенно передавать их на кухню.",
    done: ["Меню и корзина на inline-кнопках", "Заказ сохраняется в базу и приходит администратору", "Кнопка «Готов» у админа уведомляет клиента", "Рассылка акций командой /broadcast"],
    tech: ["aiogram 3, асинхронный polling", "Токен и ID админа в .env, в репозитории только пример", "Проверка кода в CI на каждый пуш"] },
];
const cats = { all: "Все", tg: "Telegram", services: "Услуги", shop: "Магазины", food: "Общепит", startup: "Стартапы" };
const caseUrl = (p) => (p.bot ? "#bot" : `projects/${p.slug}/`);
const codeUrl = (p) => `${CONFIG.repo}/tree/main/projects/${p.slug}`;

$("filters").innerHTML = Object.entries(cats)
  .map(([k, v], i) => `<button class="chip${i ? "" : " active"}" aria-pressed="${!i}" data-cat="${k}">${v}<span>${k === "all" ? projects.length : projects.filter((p) => p.cat === k).length}</span></button>`)
  .join("");

function workCard(p) {
  const preview = p.bot
    ? `<div class="work__bot"><div class="mini-msg">📋 Меню</div><div class="mini-msg mini-msg--me">☕ Капучино ×2</div><div class="mini-msg">🎉 Заказ №4821 принят!</div></div>`
    : `<img class="work__shot" src="assets/previews/${p.slug}.jpg" alt="" loading="lazy" decoding="async" data-slug="${p.slug}">`;
  return `
    <article class="work" data-cat="${p.cat}">
      <button class="work__preview${p.bot ? " work__preview--bot" : ""}" data-case="${p.slug}" aria-label="Кейс: ${p.title}">
        ${preview}
        ${p.isNew ? '<span class="work__new">Новое</span>' : ""}
        <span class="work__open">Смотреть кейс</span>
      </button>
      <div class="work__body">
        <span class="work__niche">${p.niche}</span>
        <h3>${p.title}</h3>
        <p>${p.text}</p>
        <ul class="tags">${p.tags.map((t) => `<li>${t}</li>`).join("")}</ul>
        <div class="work__links">
          <button data-case="${p.slug}">Подробнее о кейсе</button>
          <a href="${caseUrl(p)}"${p.bot ? "" : ' target="_blank" rel="noopener"'}>${p.bot ? "Демо ↓" : "Открыть ↗"}</a>
        </div>
      </div>
    </article>`;
}
$("worksGrid").innerHTML = projects.map(workCard).join("");

// Если скриншота ещё нет, показываем живой сайт в уменьшенном iframe
document.querySelectorAll(".work__shot").forEach((img) => {
  img.addEventListener("error", () => {
    const f = document.createElement("iframe");
    f.src = `projects/${img.dataset.slug}/`;
    f.title = "Превью";
    f.tabIndex = -1;
    f.setAttribute("aria-hidden", "true");
    f.loading = "lazy";
    img.replaceWith(f);
    const fit = () => { f.style.transform = `scale(${f.parentElement.clientWidth / 1280})`; };
    fit();
    new ResizeObserver(fit).observe(f.parentElement);
  }, { once: true });
});

$("filters").addEventListener("click", (e) => {
  const b = e.target.closest(".chip");
  if (!b) return;
  document.querySelectorAll(".chip").forEach((c) => {
    c.classList.toggle("active", c === b);
    c.setAttribute("aria-pressed", c === b);
  });
  document.querySelectorAll(".work").forEach((w) => {
    w.hidden = b.dataset.cat !== "all" && w.dataset.cat !== b.dataset.cat;
  });
});

// ---------- Модалка кейса ----------
const caseEl = $("case");
let caseIdx = -1;
let lastFocus = null;

function openCase(slug, push = true) {
  const i = projects.findIndex((p) => p.slug === slug);
  if (i < 0) return;
  const p = projects[i];
  caseIdx = i;
  if (!caseEl.open) {
    lastFocus = document.activeElement;
    caseEl.showModal();
    document.body.classList.add("lock");
  }
  const device = p.phone || p.bot ? "phone" : "desktop";
  caseEl.querySelector(".case__inner").innerHTML = `
    <div class="case__stage">
      <div class="case__devices" role="group" aria-label="Устройство">
        <button data-device="desktop" aria-pressed="${device === "desktop"}" ${p.bot ? "disabled" : ""}>Компьютер</button>
        <button data-device="phone" aria-pressed="${device === "phone"}">Телефон</button>
      </div>
      <div class="frame frame--${device}" id="caseFrame">
        ${p.bot
          ? `<div class="case__bot"><div class="mini-msg">Привет! 👋 Я бот кофейни «Зерно»</div><div class="mini-msg mini-msg--me">📋 Меню</div><div class="mini-msg">☕ Кофе\n• Капучино — 220 ₽\n• Латте — 240 ₽</div><div class="mini-msg mini-msg--me">✅ Оформить</div><div class="mini-msg">🎉 Заказ №4821 принят!</div><a class="btn btn--small" href="#bot" data-close>Попробовать симуляцию ↓</a></div>`
          : `<iframe src="projects/${p.slug}/${p.phone ? "?embed" : ""}" title="Демо: ${p.title}" loading="lazy"></iframe>`}
      </div>
      <p class="case__hint">${p.bot ? "Живая симуляция бота ниже на странице" : "Сайт живой: можно кликать прямо здесь"}</p>
    </div>
    <article class="case__text">
      <span class="work__niche">${p.niche}</span>
      <h2 id="caseTitle">${p.title}</h2>
      <p class="case__lead">${p.text}</p>
      <h3>Задача</h3><p>${p.goal}</p>
      <h3>Что сделано</h3><ul class="checks">${p.done.map((d) => `<li>${d}</li>`).join("")}</ul>
      <h3>Под капотом</h3><ul class="case__tech">${p.tech.map((d) => `<li>${d}</li>`).join("")}</ul>
      <ul class="tags">${p.tags.map((t) => `<li>${t}</li>`).join("")}</ul>
      <div class="case__actions">
        ${p.bot ? "" : `<a class="btn" href="${caseUrl(p)}" target="_blank" rel="noopener">Открыть сайт ↗</a>`}
        <a class="btn btn--ghost" href="${codeUrl(p)}" target="_blank" rel="noopener">Код на GitHub</a>
      </div>
      <div class="case__nav">
        <button data-step="-1">← ${projects[(i - 1 + projects.length) % projects.length].title}</button>
        <button data-step="1">${projects[(i + 1) % projects.length].title} →</button>
      </div>
    </article>`;
  caseEl.setAttribute("aria-labelledby", "caseTitle");
  fitCaseFrame();
  caseEl.querySelector(".case__scroll").scrollTop = 0;
  if (push) history.replaceState(null, "", `#case-${slug}`);
}

// В режиме «Компьютер» сайт рендерится на ширине 1280px и уменьшается под рамку, как настоящий монитор
function fitCaseFrame() {
  const frame = $("caseFrame");
  const f = frame && frame.querySelector("iframe");
  if (!f) return;
  if (frame.classList.contains("frame--desktop")) {
    const k = frame.clientWidth / 1280;
    Object.assign(f.style, { width: "1280px", height: `${frame.clientHeight / k}px`, transform: `scale(${k})`, transformOrigin: "0 0" });
  } else {
    Object.assign(f.style, { width: "", height: "", transform: "" });
  }
}
addEventListener("resize", () => caseEl.open && fitCaseFrame());

function closeCase() {
  if (!caseEl.open) return;
  caseEl.close();
}
caseEl.addEventListener("close", () => {
  document.body.classList.remove("lock");
  caseEl.querySelector(".case__inner").innerHTML = "";
  if (location.hash.startsWith("#case-")) history.replaceState(null, "", "#works");
  if (lastFocus) lastFocus.focus();
});
caseEl.addEventListener("click", (e) => {
  if (e.target === caseEl) return closeCase();
  const t = e.target.closest("button, a");
  if (!t) return;
  if (t.matches("[data-close]")) {
    closeCase();
    if (t.getAttribute("href") === "#bot") $("bot").scrollIntoView({ behavior: "smooth" });
    return;
  }
  if (t.dataset.step) openCase(projects[(caseIdx + +t.dataset.step + projects.length) % projects.length].slug);
  if (t.dataset.device && !t.disabled) {
    $("caseFrame").className = `frame frame--${t.dataset.device}`;
    caseEl.querySelectorAll("[data-device]").forEach((b) => b.setAttribute("aria-pressed", b === t));
    // ждём, пока рамка поменяет размер
    setTimeout(fitCaseFrame, 460);
    fitCaseFrame();
  }
});
caseEl.addEventListener("keydown", (e) => {
  if (e.target.closest("input, textarea")) return;
  if (e.key === "ArrowRight") openCase(projects[(caseIdx + 1) % projects.length].slug);
  if (e.key === "ArrowLeft") openCase(projects[(caseIdx - 1 + projects.length) % projects.length].slug);
});
document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-case]");
  if (t && !caseEl.contains(t)) openCase(t.dataset.case);
});
// Прямые ссылки вида #case-florist
const fromHash = () => {
  const m = location.hash.match(/^#case-([\w-]+)$/);
  if (m) openCase(m[1], false);
};
addEventListener("hashchange", fromHash);
fromHash();

// ---------- Услуги ----------
const icon = (d) => `<svg viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
const services = [
  [icon('<path d="M17 8h1a4 4 0 0 1 0 8h-1M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V8zM6 2v3M10 2v3M14 2v3"/>'), "Сайт для кафе и ресторана", "Меню с ценами, бронь столика, карта, часы работы. Гость за минуту понимает, почему стоит прийти именно к вам."],
  [icon('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><path d="M14 14h3v3h-3zM20 14v.01M14 20h.01M17 17h4v4"/>'), "QR-меню", "Электронное меню по QR-коду на столе. Цены меняете сами за секунды, без перепечатки."],
  [icon('<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18M9 16l2 2 4-4"/>'), "Онлайн-запись", "Для салонов, клиник, барбершопов и автосервисов: услуга, мастер, время. Заявка сразу приходит в Telegram."],
  [icon('<path d="M21 4 3 11l6 2 2 6 3-4 5 4 2-15z"/><path d="m9 13 8-6"/>'), "Telegram-боты", "Приём заказов, запись, рассылки, ответы на частые вопросы, оплата. Бот работает круглосуточно."],
  [icon('<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>'), "Магазины и каталоги", "Каталог с фильтрами, корзина, оформление заказа. Заказы приходят в Telegram или CRM."],
  [icon('<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 10h8M8 14h2M14 14h2M8 18h2M14 18h2"/>'), "Калькуляторы и квизы", "Расчёт стоимости прямо на сайте. Клиент видит цену и оставляет заявку охотнее."],
];
$("servicesGrid").innerHTML = services
  .map(([ic, t, d]) => `<article class="card"><div class="card__icon">${ic}</div><h3>${t}</h3><p>${d}</p></article>`)
  .join("");

// ---------- Появление при прокрутке ----------
const io = new IntersectionObserver((entries) => entries.forEach((e) => {
  if (e.isIntersecting) { e.target.classList.add("visible"); io.unobserve(e.target); }
}), { threshold: 0.1 });
document.querySelectorAll(".card, .work, .steps li, .why__item, .faq, .calc").forEach((el) => {
  el.classList.add("reveal");
  io.observe(el);
});

// ---------- Живость: подсветка за курсором, «магнитные» кнопки, счётчики ----------
const finePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
if (finePointer && !reduceMotion) {
  document.addEventListener("pointermove", (e) => {
    const el = e.target.closest(".card, .work, .why__item, .steps li");
    if (!el) return;
    const r = el.getBoundingClientRect();
    el.style.setProperty("--mx", `${e.clientX - r.left}px`);
    el.style.setProperty("--my", `${e.clientY - r.top}px`);
  });
  document.querySelectorAll(".hero__actions .btn, .contact__links .btn, .header .btn").forEach((b) => {
    b.addEventListener("pointermove", (e) => {
      const r = b.getBoundingClientRect();
      b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px, ${(e.clientY - r.top - r.height / 2) * 0.3}px)`;
    });
    b.addEventListener("pointerleave", () => { b.style.transform = ""; });
  });
}

const countIO = new IntersectionObserver((entries) => entries.forEach((e) => {
  if (!e.isIntersecting) return;
  const el = e.target;
  const to = +el.dataset.count;
  countIO.unobserve(el);
  if (reduceMotion) return;
  el.style.minWidth = `${el.getBoundingClientRect().width}px`;
  el.style.fontVariantNumeric = "tabular-nums";
  const start = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - start) / 1200);
    el.textContent = Math.round(to * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  setTimeout(() => { el.textContent = to; }, 1400);
}));
document.querySelectorAll("[data-count]").forEach((el) => countIO.observe(el));

// ---------- Симуляция Telegram-бота ----------
const chat = $("chat");
const keys = $("keys");
const menu = {
  "☕ Кофе": [{ name: "Капучино", price: 220 }, { name: "Латте", price: 240 }, { name: "Флэт уайт", price: 260 }],
  "🥐 Выпечка": [{ name: "Круассан", price: 180 }, { name: "Синнабон", price: 210 }],
  "🍰 Десерты": [{ name: "Чизкейк", price: 290 }, { name: "Тирамису", price: 320 }],
};
let cart = [];
const cartTotal = () => cart.reduce((s, i) => s + i.price, 0);

function addMsg(text, who = "bot") {
  const el = document.createElement("div");
  el.className = `msg msg--${who}`;
  el.textContent = text;
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function setKeys(buttons) {
  keys.innerHTML = "";
  buttons.forEach(({ label, action, wide }) => {
    const b = document.createElement("button");
    b.textContent = label;
    if (wide) b.classList.add("wide");
    b.addEventListener("click", () => {
      addMsg(label, "user");
      keys.innerHTML = "";
      botReply(action);
    });
    keys.appendChild(b);
  });
}

function botReply(action) {
  $("botStatus").textContent = "печатает…";
  setTimeout(() => {
    $("botStatus").textContent = "бот";
    action();
  }, 550);
}

function showMain() {
  addMsg("Выберите, что хотите сделать 👇");
  setKeys([
    { label: "📋 Меню", action: showCategories },
    { label: `🛒 Корзина (${cart.length})`, action: showCart },
    { label: "📍 Адрес и часы", action: showInfo, wide: true },
  ]);
}

function showCategories() {
  addMsg("Выберите категорию:");
  setKeys([
    ...Object.keys(menu).map((cat) => ({ label: cat, action: () => showCategory(cat) })),
    { label: "⬅️ Назад", action: showMain },
  ]);
}

function showCategory(cat) {
  addMsg(`${cat}\n\n` + menu[cat].map((i) => `• ${i.name} — ${i.price} ₽`).join("\n"));
  setKeys([
    ...menu[cat].map((item) => ({
      label: `+ ${item.name}`,
      action: () => {
        cart.push(item);
        addMsg(`✅ ${item.name} в корзине.\nСумма: ${cartTotal()} ₽`);
        showCategory(cat);
      },
    })),
    { label: "⬅️ Категории", action: showCategories },
    { label: `🛒 Корзина (${cart.length})`, action: showCart },
  ]);
}

function showCart() {
  if (!cart.length) {
    addMsg("Корзина пока пуста 🙂");
    return showMain();
  }
  addMsg("🛒 Ваш заказ:\n\n" + cart.map((i) => `• ${i.name} — ${i.price} ₽`).join("\n") + `\n\nИтого: ${cartTotal()} ₽`);
  setKeys([
    { label: "✅ Оформить", action: checkout },
    { label: "🗑 Очистить", action: () => { cart = []; addMsg("Корзина очищена."); showMain(); } },
    { label: "⬅️ В меню", action: showMain, wide: true },
  ]);
}

function checkout() {
  const num = Math.floor(1000 + Math.random() * 9000);
  addMsg(`🎉 Заказ №${num} принят!\nСумма: ${cartTotal()} ₽\n\nБудет готов через 10–15 минут.`);
  cart = [];
  setTimeout(() => addMsg("☕ Ваш заказ готов! Заберите его на кассе."), 1800);
  setTimeout(() => setKeys([{ label: "🔄 Начать заново", action: startBot, wide: true }]), 2000);
}

function showInfo() {
  addMsg("📍 ул. Примерная, 12\n🕗 Ежедневно 8:00–22:00\n📞 +7 (900) 000-00-00");
  showMain();
}

function startBot() {
  chat.innerHTML = "";
  cart = [];
  addMsg("Привет! 👋 Я бот кофейни «Зерно».\nПомогу сделать заказ без очереди.");
  showMain();
}
startBot();

// ---------- Калькулятор стоимости ----------
const calcTypes = [
  { id: "landing", name: "Лендинг", desc: "1 страница", price: 15000, days: 5 },
  { id: "site", name: "Сайт заведения", desc: "до 5 страниц", price: 30000, days: 10 },
  { id: "shop", name: "Магазин / каталог", desc: "корзина, фильтры", price: 45000, days: 14 },
  { id: "bot", name: "Telegram-бот", desc: "заказы, запись", price: 10000, days: 4 },
];
const calcOpts = [
  { id: "booking", name: "Онлайн-запись или бронь", price: 7000, days: 2 },
  { id: "calc", name: "Калькулятор или квиз", price: 6000, days: 2 },
  { id: "tg", name: "Заявки в Telegram", price: 2000, days: 0 },
  { id: "bot", name: "Telegram-бот к сайту", price: 10000, days: 3 },
  { id: "admin", name: "Админка для цен и меню", price: 12000, days: 3 },
  { id: "texts", name: "Тексты и подбор фото", price: 5000, days: 1 },
];
const calcState = { type: "site", opts: new Set(["tg"]), k: 1 };

$("calcTypes").innerHTML = calcTypes
  .map((t) => `<button type="button" class="calc__type${t.id === calcState.type ? " active" : ""}" data-id="${t.id}"><b>${t.name}</b><small>${t.desc} · от ${t.price.toLocaleString("ru-RU")} ₽</small></button>`)
  .join("");
$("calcOpts").innerHTML = calcOpts
  .map((o) => `<label class="calc__opt"><input type="checkbox" value="${o.id}"${calcState.opts.has(o.id) ? " checked" : ""}><span>${o.name}</span><em>+${o.price.toLocaleString("ru-RU")} ₽</em></label>`)
  .join("");

$("calcTypes").addEventListener("click", (e) => {
  const b = e.target.closest(".calc__type");
  if (!b) return;
  calcState.type = b.dataset.id;
  document.querySelectorAll(".calc__type").forEach((x) => x.classList.toggle("active", x === b));
  renderCalc();
});
$("calcOpts").addEventListener("change", (e) => {
  e.target.checked ? calcState.opts.add(e.target.value) : calcState.opts.delete(e.target.value);
  renderCalc();
});
$("calcSpeed").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  calcState.k = +b.dataset.k;
  $("calcSpeed").querySelectorAll("button").forEach((x) => x.classList.toggle("active", x === b));
  renderCalc();
});

let calcShown = 0;
let calcText = "";
function renderCalc() {
  const type = calcTypes.find((t) => t.id === calcState.type);
  // Бот к боту не добавляем
  const opts = calcOpts.filter((o) => calcState.opts.has(o.id) && !(type.id === "bot" && o.id === "bot"));
  const base = type.price + opts.reduce((s, o) => s + o.price, 0);
  const sum = Math.round((base * calcState.k) / 1000) * 1000;
  const days = Math.max(3, Math.ceil((type.days + opts.reduce((s, o) => s + o.days, 0)) / (calcState.k > 1 ? 1.5 : 1)));
  $("calcList").innerHTML = [`<li><span>${type.name}</span><span>${type.price.toLocaleString("ru-RU")} ₽</span></li>`,
    ...opts.map((o) => `<li><span>${o.name}</span><span>+${o.price.toLocaleString("ru-RU")} ₽</span></li>`),
    calcState.k > 1 ? `<li><span>Срочность</span><span>+30%</span></li>` : ""].join("");
  $("calcDays").textContent = `Срок: ~${days} ${days % 10 === 1 && days !== 11 ? "день" : days % 10 >= 2 && days % 10 <= 4 && (days < 10 || days > 20) ? "дня" : "дней"}`;
  calcText = `Здравствуйте! Посчитал проект на сайте:\n• ${type.name}\n${opts.map((o) => `• ${o.name}`).join("\n")}${calcState.k > 1 ? "\n• Срочно" : ""}\nИтого: от ${sum.toLocaleString("ru-RU")} ₽, ~${days} дн.`;
  animateNumber(sum);
}
function animateNumber(to) {
  // Страховка: если браузер не даёт анимировать (свёрнутое окно), итог всё равно появится
  clearTimeout(animateNumber.done);
  animateNumber.done = setTimeout(() => {
    calcShown = to;
    $("calcSum").textContent = `от ${to.toLocaleString("ru-RU")} ₽`;
  }, 500);
  const from = calcShown;
  const start = performance.now();
  const step = (t) => {
    const p = Math.min(1, (t - start) / 450);
    calcShown = Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3)));
    $("calcSum").textContent = `от ${calcShown.toLocaleString("ru-RU")} ₽`;
    if (p < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
$("calcSend").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(calcText);
    toast("Расчёт скопирован. Вставьте его в чат");
  } catch {
    toast("Откройте чат и опишите проект");
  }
  window.open(`https://t.me/${CONFIG.telegram}`, "_blank", "noopener");
});
renderCalc();

// ---------- Уведомления ----------
let toastTimer;
function toast(msg) {
  $("toast").textContent = msg;
  $("toast").classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("toast").classList.remove("show"), 2600);
}
