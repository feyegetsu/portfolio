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
const niches = ["Кофейни", "Рестораны", "Барбершопы", "Салоны красоты", "Клиники", "Фитнес", "Автосервисы", "Цветы", "Недвижимость", "Стартапы"];
$("ticker").innerHTML = [...niches, ...niches].map((n) => `<span>${n}</span>`).join("");

// ---------- Работы ----------
const projects = [
  { slug: "cafe", title: "Кофейня «Зерно»", niche: "Общепит", cat: "food",
    text: "Сайт кофейни с меню по категориям и бронью столика.", tags: ["Меню", "Бронь", "Адаптив"] },
  { slug: "florist", title: "Пион & Ко", niche: "Интернет-магазин", cat: "shop",
    text: "Магазин цветов: каталог, фильтры, корзина с сохранением, оформление доставки.", tags: ["Корзина", "Фильтры", "localStorage"] },
  { slug: "barbershop", title: "Барбершоп BLADE", niche: "Красота", cat: "services",
    text: "Онлайн-запись в 3 шага: услуга, мастер, свободное время.", tags: ["Онлайн-запись", "Слоты"] },
  { slug: "dental", title: "Стоматология «Белая линия»", niche: "Медицина", cat: "services",
    text: "Клиника с прайсом по вкладкам и квизом, который считает стоимость лечения.", tags: ["Квиз", "Прайс", "Лиды"] },
  { slug: "fitness", title: "Фитнес-клуб PULSE", niche: "Спорт", cat: "services",
    text: "Расписание на неделю с записью на занятия и абонементы с переключением периода.", tags: ["Расписание", "Тарифы"] },
  { slug: "autoservice", title: "Автосервис «МоторЛайн»", niche: "Авто", cat: "services",
    text: "Калькулятор стоимости ремонта и отслеживание статуса машины по номеру заказа.", tags: ["Калькулятор", "Статус заказа"] },
  { slug: "realty", title: "Агентство «Квадрат»", niche: "Недвижимость", cat: "shop",
    text: "Каталог квартир с фильтрами и избранным, карточка объекта, ипотечный калькулятор.", tags: ["Каталог", "Ипотека", "Модалки"] },
  { slug: "saas", title: "Taskly", niche: "IT-стартап", cat: "startup",
    text: "Лендинг SaaS-сервиса с интерактивной канбан-доской и расчётом тарифа по числу людей.", tags: ["Drag & Drop", "Тарифы"] },
  { slug: "cafe-bot", title: "Бот для заказов", niche: "Telegram-бот", cat: "bots", bot: true,
    text: "Бот кафе на aiogram 3: меню, корзина, заказы в SQLite, уведомления админу, рассылки.", tags: ["Python", "aiogram", "SQLite"] },
];
const cats = { all: "Все", food: "Общепит", services: "Услуги", shop: "Магазины", startup: "Стартапы", bots: "Боты" };

$("filters").innerHTML = Object.entries(cats)
  .map(([k, v], i) => `<button class="chip${i ? "" : " active"}" role="tab" aria-selected="${!i}" data-cat="${k}">${v}</button>`)
  .join("");

function workCard(p) {
  const href = p.bot ? "#bot" : `projects/${p.slug}/`;
  const preview = p.bot
    ? `<div class="work__bot"><div class="mini-msg">📋 Меню</div><div class="mini-msg mini-msg--me">☕ Капучино ×2</div><div class="mini-msg">🎉 Заказ №4821 принят!</div></div>`
    : `<iframe data-src="projects/${p.slug}/" title="Превью: ${p.title}" tabindex="-1" aria-hidden="true" loading="lazy"></iframe>`;
  return `
    <article class="work" data-cat="${p.cat}">
      <a class="work__preview${p.bot ? " work__preview--bot" : ""}" href="${href}" aria-label="Открыть ${p.title}">
        ${preview}
        <span class="work__open">${p.bot ? "Попробовать ↓" : "Открыть демо ↗"}</span>
      </a>
      <div class="work__body">
        <span class="work__niche">${p.niche}</span>
        <h3>${p.title}</h3>
        <p>${p.text}</p>
        <ul class="tags">${p.tags.map((t) => `<li>${t}</li>`).join("")}</ul>
        <div class="work__links">
          <a href="${href}">${p.bot ? "Демо в браузере" : "Смотреть сайт"}</a>
          <a href="${CONFIG.repo}/tree/main/projects/${p.slug}" target="_blank" rel="noopener">Код →</a>
        </div>
      </div>
    </article>`;
}
$("worksGrid").innerHTML = projects.map(workCard).join("");

$("filters").addEventListener("click", (e) => {
  const b = e.target.closest(".chip");
  if (!b) return;
  document.querySelectorAll(".chip").forEach((c) => {
    c.classList.toggle("active", c === b);
    c.setAttribute("aria-selected", c === b);
  });
  document.querySelectorAll(".work").forEach((w) => {
    w.hidden = b.dataset.cat !== "all" && w.dataset.cat !== b.dataset.cat;
  });
});

// Живые превью: сайт рендерится в iframe шириной 1280px и масштабируется под карточку
const fitFrame = (frame) => { frame.style.transform = `scale(${frame.parentElement.clientWidth / 1280})`; };
const ro = new ResizeObserver((entries) => entries.forEach((e) => {
  const f = e.target.querySelector("iframe");
  if (f) fitFrame(f);
}));
const frameIO = new IntersectionObserver((entries) => entries.forEach((e) => {
  if (!e.isIntersecting) return;
  const f = e.target;
  f.src = f.dataset.src;
  fitFrame(f);
  ro.observe(f.parentElement);
  frameIO.unobserve(f);
}), { rootMargin: "300px" });
document.querySelectorAll(".work iframe").forEach((f) => frameIO.observe(f));

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
