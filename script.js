// Мобильное меню
const burger = document.getElementById("burger");
const nav = document.getElementById("nav");
burger.addEventListener("click", () => {
  nav.classList.toggle("open");
  burger.classList.toggle("open");
});
nav.querySelectorAll("a").forEach((a) =>
  a.addEventListener("click", () => {
    nav.classList.remove("open");
    burger.classList.remove("open");
  })
);

document.getElementById("year").textContent = new Date().getFullYear();

// Плавное появление блоков при прокрутке
const io = new IntersectionObserver(
  (entries) =>
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("visible");
        io.unobserve(e.target);
      }
    }),
  { threshold: 0.12 }
);
document.querySelectorAll(".card, .work, .steps li, .price, .faq").forEach((el) => {
  el.classList.add("reveal");
  io.observe(el);
});

// ---------- Симуляция Telegram-бота ----------
const chat = document.getElementById("chat");
const keys = document.getElementById("keys");

const menu = {
  "☕ Кофе": [
    { name: "Капучино", price: 220 },
    { name: "Латте", price: 240 },
    { name: "Флэт уайт", price: 260 },
  ],
  "🥐 Выпечка": [
    { name: "Круассан", price: 180 },
    { name: "Синнабон", price: 210 },
  ],
  "🍰 Десерты": [
    { name: "Чизкейк", price: 290 },
    { name: "Тирамису", price: 320 },
  ],
};
let cart = [];

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
  const typing = document.createElement("div");
  typing.className = "typing";
  typing.textContent = "печатает…";
  chat.appendChild(typing);
  chat.scrollTop = chat.scrollHeight;
  setTimeout(() => {
    typing.remove();
    action();
  }, 600);
}

const cartTotal = () => cart.reduce((s, i) => s + i.price, 0);

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
        addMsg(`✅ ${item.name} добавлен в корзину.\nСумма: ${cartTotal()} ₽`);
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
  addMsg(`🎉 Заказ №${num} принят!\nСумма: ${cartTotal()} ₽\n\nБудет готов через 10–15 минут. Мы пришлём уведомление.`);
  setTimeout(() => addMsg("☕ Ваш заказ готов! Заберите его на кассе."), 1800);
  cart = [];
  setTimeout(() => {
    setKeys([{ label: "🔄 Начать заново", action: start, wide: true }]);
  }, 2000);
}

function showInfo() {
  addMsg("📍 ул. Примерная, 12\n🕗 Ежедневно 8:00–22:00\n📞 +7 (900) 000-00-00");
  showMain();
}

function start() {
  chat.innerHTML = "";
  cart = [];
  addMsg("Привет! 👋 Я бот кофейни «Зерно».\nПомогу сделать заказ без очереди.");
  showMain();
}

start();
