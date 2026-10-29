/* Админ-панель. Работает с window.PortfolioAPI: в демо-режиме данные в браузере, с ?api=… — с настоящим бэкендом. */
(() => {
  const api = window.PortfolioAPI;
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const rub = (n) => `${Number(n || 0).toLocaleString("ru-RU")} ₽`;
  const SITE_NAME = Object.fromEntries(api.SITES.map((s) => [s.slug, s.name]));
  const ROLE_NAME = { owner: "Владелец", admin: "Администратор", staff: "Сотрудник" };
  const ROLE_LEVEL = { staff: 1, admin: 2, owner: 3 };

  const LEAD_STATUS = { new: "Новая", in_progress: "В работе", done: "Готово", cancelled: "Отмена" };
  const BOOKING_STATUS = { confirmed: "Подтверждена", done: "Пришёл", cancelled: "Отменена" };
  const ORDER_STATUS = { new: "Новый", cooking: "Готовится", delivering: "В пути", done: "Выполнен", cancelled: "Отменён" };
  const KIND = {
    table: "Бронь столика", consult: "Консультация", quiz: "Квиз", viewing: "Просмотр", repair: "Запись на ремонт",
    signup: "Регистрация", trial: "Пробная тренировка", subscribe: "Подписка", class: "Занятие",
  };

  // Бэкенд отдаёт created_at в UTC без часового пояса, демо — с «Z»; показываем в местном времени
  const fmtDate = (s) => new Date(/Z|[+-]\d\d:\d\d$/.test(s) ? s : `${s}Z`)
    .toLocaleString("ru-RU", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });

  const state = { user: null, view: "overview", site: "", leadStatus: "", q: "", offset: 0, known: null };

  // ---------- Уведомления ----------
  let tt;
  function toast(msg, err = false) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.toggle("err", err);
    t.classList.add("show");
    clearTimeout(tt);
    tt = setTimeout(() => t.classList.remove("show"), 2600);
  }
  async function run(fn, okMsg) {
    try {
      const r = await fn();
      if (okMsg) toast(okMsg);
      return r;
    } catch (e) {
      if (e.status === 401) return logout();
      toast(e.message || "Ошибка", true);
      throw e;
    }
  }

  // ---------- Вход ----------
  function showLogin() {
    $("appView").hidden = true;
    $("loginView").hidden = false;
    const demo = api.mode === "demo";
    $("loginHint").textContent = demo
      ? "Демо-режим: данные хранятся только в вашем браузере. Войдите одним из тестовых аккаунтов."
      : `Подключено к API: ${api.base}`;
    $("demoUsers").innerHTML = demo
      ? `<span class="muted">Быстрый вход</span>
         <button type="button" data-email="demo@feyegetsu.dev">Владелец<small>все сайты, все права · demo@feyegetsu.dev / demo</small></button>
         <button type="button" data-email="cafe@feyegetsu.dev">Администратор кофейни<small>только «Зерно», без каталога и команды</small></button>`
      : "";
  }
  $("demoUsers").addEventListener("click", (e) => {
    const b = e.target.closest("[data-email]");
    if (!b) return;
    $("loginForm").email.value = b.dataset.email;
    $("loginForm").password.value = "demo";
    $("loginForm").requestSubmit();
  });
  $("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = e.target;
    const btn = f.querySelector("button[type=submit]");
    btn.disabled = true;
    $("loginError").textContent = "";
    try {
      state.user = await api.login(f.email.value, f.password.value);
      start();
    } catch (err) {
      $("loginError").textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
  function logout() {
    api.logout();
    state.user = null;
    showLogin();
  }

  // ---------- Каркас ----------
  const ICON = {
    overview: '<path d="M3 13h8V3H3zM13 21h8V11h-8zM3 21h8v-6H3zM13 3v6h8V3z"/>',
    leads: '<path d="M4 4h16v16H4z"/><path d="M4 9h16M9 4v16"/>',
    bookings: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    orders: '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4zM3 6h18M16 10a4 4 0 0 1-8 0"/>',
    catalog: '<path d="M4 6h16M4 12h16M4 18h10"/>',
    team: '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M17 11a3 3 0 1 0 0-6M22 21a6 6 0 0 0-4-5.6"/>',
  };
  const VIEWS = [
    ["overview", "Обзор", "staff"], ["leads", "Заявки", "staff"], ["bookings", "Записи", "staff"],
    ["orders", "Заказы", "staff"], ["catalog", "Каталог", "admin"], ["team", "Команда", "owner"],
  ];
  const can = (role) => ROLE_LEVEL[state.user.role] >= ROLE_LEVEL[role];
  const mySites = () => (state.user.sites === null ? api.SITES.map((s) => s.slug) : state.user.sites);

  function renderShell() {
    $("loginView").hidden = true;
    $("appView").hidden = false;
    const u = state.user;
    $("userBox").innerHTML = `<span class="avatar">${esc(u.name[0])}</span>
      <span class="user__info"><b>${esc(u.name)}</b><br><small>${ROLE_NAME[u.role]}</small></span>
      <button class="btn btn--sm" id="logout">Выйти</button>`;
    $("logout").onclick = logout;
    $("nav").innerHTML = VIEWS.filter(([, , r]) => can(r))
      .map(([id, title]) => `<button data-view="${id}"><svg viewBox="0 0 24 24">${ICON[id]}</svg>${title}<span class="count" id="count-${id}" hidden></span></button>`).join("");
    const sites = mySites();
    $("siteFilter").innerHTML = (sites.length > 1 ? '<option value="">Все сайты</option>' : "") +
      sites.map((s) => `<option value="${s}">${esc(SITE_NAME[s])}</option>`).join("");
    if (!sites.includes(state.site)) state.site = sites.length > 1 ? "" : sites[0];
    $("siteFilter").value = state.site;
    $("modeBadge").className = `mode ${api.mode}`;
    $("modeBadge").innerHTML = api.mode === "demo"
      ? `<b>Демо-режим</b>Данные хранятся в вашем браузере. Оставьте заявку на любом демо-сайте — она появится здесь.<button class="btn btn--sm" id="resetDemo">Сбросить демо-данные</button>`
      : `<b>API подключено</b><span style="word-break:break-all">${esc(api.base)}</span>`;
    const reset = $("resetDemo");
    if (reset) reset.onclick = () => { api.reset(); toast("Демо-данные сброшены"); logout(); };
  }
  $("nav").addEventListener("click", (e) => {
    const b = e.target.closest("[data-view]");
    if (b) go(b.dataset.view);
  });
  $("siteFilter").addEventListener("change", (e) => { state.site = e.target.value; state.offset = 0; render(); });

  function go(view) {
    const allowed = VIEWS.find(([id, , r]) => id === view && can(r));
    state.view = allowed ? view : "overview";
    state.offset = 0;
    history.replaceState(null, "", `#${state.view}`);
    render();
  }

  async function render() {
    document.querySelectorAll("[data-view]").forEach((b) => {
      if (b.dataset.view === state.view) b.setAttribute("aria-current", "page");
      else b.removeAttribute("aria-current");
    });
    $("viewTitle").textContent = VIEWS.find(([id]) => id === state.view)[1];
    try {
      await ({ overview, leads, bookings, orders, catalog, team })[state.view]();
    } catch (e) {
      if (e.status === 401) return logout();
      $("content").innerHTML = `<div class="empty">Не удалось загрузить: ${esc(e.message)}</div>`;
    }
    updateBadges();
  }

  async function updateBadges() {
    try {
      const s = await api.admin.stats({ site: state.site || undefined });
      const c = $("count-leads");
      if (c) { c.textContent = s.new_leads; c.hidden = !s.new_leads; }
    } catch { /* значок не критичен */ }
  }

  const siteFilter = () => (state.site ? { site: state.site } : {});
  const siteTag = (s) => `<span class="site-tag">${esc(SITE_NAME[s] || s)}</span>`;
  const statusSelect = (kind, id, value, map) =>
    `<select class="status s-${value}" data-${kind}="${id}" aria-label="Статус">${Object.entries(map).map(([k, v]) => `<option value="${k}"${k === value ? " selected" : ""}>${v}</option>`).join("")}</select>`;

  // ---------- Обзор ----------
  async function overview() {
    const [s, latest] = await Promise.all([api.admin.stats(siteFilter()), api.admin.leads({ ...siteFilter(), limit: 6 })]);
    const max = Math.max(1, ...s.by_day.map((d) => d.count));
    const siteTotal = Math.max(1, ...Object.values(s.by_site));
    $("content").innerHTML = `
      <div class="kpis">
        <div class="kpi"><span>Заявки</span><b>${s.leads}</b><small>${s.new_leads} новых</small></div>
        <div class="kpi"><span>Записи</span><b>${s.bookings}</b><small>на услуги и занятия</small></div>
        <div class="kpi"><span>Заказы</span><b>${s.orders}</b><small>доставка и самовывоз</small></div>
        <div class="kpi"><span>Выручка по заказам</span><b>${rub(s.revenue)}</b><small>без отменённых</small></div>
      </div>
      <div class="grid2">
        <div class="panel"><h2>Обращения за 14 дней</h2>
          <div class="chart" role="img" aria-label="Обращения по дням">${s.by_day.map((d) => {
            const day = new Date(d.date + "T12:00:00");
            return `<div class="chart__bar" title="${day.toLocaleDateString("ru-RU")}: ${d.count}"><em>${d.count || ""}</em><i style="height:${(d.count / max) * 100}%"></i><small>${day.getDate()}</small></div>`;
          }).join("")}</div>
        </div>
        <div class="panel"><h2>По сайтам</h2><div class="bars">${Object.entries(s.by_site).sort((a, b) => b[1] - a[1]).map(([slug, n]) =>
          `<div><span>${esc(SITE_NAME[slug])}<b>${n}</b></span><i style="--w:${(n / siteTotal) * 100}%"></i></div>`).join("") || '<p class="muted">Пока пусто</p>'}</div></div>
      </div>
      <div class="panel"><h2>Последние заявки <button class="btn btn--sm" data-goto="leads">Все заявки →</button></h2>${leadTable(latest.items, true)}</div>
      ${api.mode === "demo" ? `<div class="notice">💡 Откройте любой демо-сайт в соседней вкладке и оставьте заявку или оформите заказ. Здесь она появится сама, без перезагрузки.</div>` : ""}`;
    $("content").querySelector("[data-goto]").onclick = () => go("leads");
  }

  // ---------- Заявки ----------
  // Поля из форм сайтов: подписи и формат значений для человека, а не для программиста
  const FIELD = {
    object: ["Объект"], price: ["Цена"], doctor: ["Врач"], result: ["Подобрано"], range: ["Стоимость"], time: ["Время"],
    date: ["Дата", (v) => (/^\d{4}-\d\d-\d\d$/.test(v) ? new Date(`${v}T12:00:00`).toLocaleDateString("ru-RU", { day: "numeric", month: "long" }) : v)],
    guests: ["Гостей"], car: ["Машина"], works: ["Работы"], total: ["Сумма", rub], seats: ["Участников"],
    yearly: ["Оплата", (v) => (v ? "за год" : "помесячно")], email: ["Почта"], master: ["Мастер"], service: ["Услуга"], comment: ["Комментарий"],
  };
  const fmtValue = (v) => (Array.isArray(v) ? v.map(fmtValue).join(", ")
    : v && typeof v === "object" ? Object.values(v).map(fmtValue).join(", ")
    : typeof v === "boolean" ? (v ? "да" : "нет") : String(v));
  function leadDetails(l) {
    const rows = Object.entries(l.data || {})
      .filter(([k, v]) => v !== "" && v != null && !(k === "email" && v === l.email))
      .map(([k, v]) => {
        const [label, fmt] = FIELD[k] || [k];
        return `<div><dt>${esc(label)}</dt><dd>${esc(fmt ? fmt(v) : fmtValue(v))}</dd></div>`;
      });
    if (!l.message && !rows.length) return '<span class="muted">—</span>';
    return `${l.message ? `<p class="lead-msg">${esc(l.message)}</p>` : ""}${rows.length ? `<dl class="kv">${rows.join("")}</dl>` : ""}`;
  }

  function leadTable(items, compact = false) {
    if (!items.length) return '<div class="empty">Заявок пока нет</div>';
    return `<div class="table-wrap"><table class="cards">
      <thead><tr><th>Дата</th><th>Сайт</th><th>Тип</th><th>Клиент</th>${compact ? "" : "<th>Детали</th>"}<th class="center">Статус</th></tr></thead>
      <tbody>${items.map((l) => `<tr data-id="lead-${l.id}">
        <td class="mono" data-label="Дата">${fmtDate(l.created_at)}</td>
        <td data-label="Сайт">${siteTag(l.site)}</td>
        <td data-label="Тип">${esc(KIND[l.kind] || l.kind)}</td>
        <td data-label="Клиент">${esc(l.name || "—")}<small>${l.phone ? `<a href="tel:${esc(l.phone)}">${esc(l.phone)}</a>` : esc(l.email)}</small></td>
        ${compact ? "" : `<td data-label="Детали" class="wide">${leadDetails(l)}</td>`}
        <td class="center" data-label="Статус">${statusSelect("lead", l.id, l.status, LEAD_STATUS)}</td>
      </tr>`).join("")}</tbody></table></div>`;
  }

  async function leads() {
    const limit = 20;
    const data = await api.admin.leads({ ...siteFilter(), status: state.leadStatus, q: state.q, limit, offset: state.offset });
    $("content").innerHTML = `
      <div class="toolbar">
        <input type="search" id="q" placeholder="Поиск по имени, телефону, комментарию" value="${esc(state.q)}" aria-label="Поиск">
        <div class="chips" role="group" aria-label="Статус">${[["", "Все"], ...Object.entries(LEAD_STATUS)].map(([k, v]) =>
          `<button class="chip" data-st="${k}" aria-pressed="${state.leadStatus === k}">${v}</button>`).join("")}</div>
        <button class="btn" id="exportCsv">Выгрузить CSV</button>
      </div>
      ${leadTable(data.items)}
      <div class="pager"><span>Показано ${data.items.length ? state.offset + 1 : 0}–${state.offset + data.items.length} из ${data.total}</span>
        <span><button class="btn btn--sm" id="prev" ${state.offset ? "" : "disabled"}>←</button>
        <button class="btn btn--sm" id="next" ${state.offset + limit < data.total ? "" : "disabled"}>→</button></span></div>`;
    let timer;
    $("q").addEventListener("input", (e) => {
      clearTimeout(timer);
      timer = setTimeout(() => { state.q = e.target.value; state.offset = 0; leads().then(() => { const q = $("q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }); }, 300);
    });
    $("content").querySelectorAll("[data-st]").forEach((b) => b.onclick = () => { state.leadStatus = b.dataset.st; state.offset = 0; leads(); });
    $("prev").onclick = () => { state.offset = Math.max(0, state.offset - limit); leads(); };
    $("next").onclick = () => { state.offset += limit; leads(); };
    $("exportCsv").onclick = async () => {
      const csv = await run(() => api.admin.exportLeads(siteFilter()));
      // Файл формируется в браузере; в песочнице артефакта загрузка может быть недоступна, тогда покажем подсказку
      try {
        const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
        const a = Object.assign(document.createElement("a"), { href: url, download: "leads.csv" });
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        toast("Файл leads.csv готов");
      } catch {
        toast("Браузер заблокировал загрузку", true);
      }
    };
  }

  // ---------- Записи ----------
  async function bookings() {
    const data = await api.admin.bookings({ ...siteFilter(), limit: 100 });
    const items = [...data.items].sort((a, b) => (a.starts_at > b.starts_at ? 1 : -1));
    const groups = {};
    for (const b of items) (groups[b.starts_at.slice(0, 10)] ||= []).push(b);
    $("content").innerHTML = items.length ? Object.entries(groups).map(([day, list]) => `
      <div class="day-group"><h3>${new Date(day + "T12:00:00").toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}</h3>
        ${list.map((b) => `<div class="slot ${b.status === "cancelled" ? "cancelled" : ""}" data-id="booking-${b.id}">
          <time>${b.starts_at.slice(11, 16)}</time>
          <div><b>${esc(b.name)}</b> · <span class="mono">${esc(b.phone)}</span><br><small class="muted">${siteTag(b.site)} ${esc(b.resource)}${b.service ? " · " + esc(b.service) : ""}</small></div>
          <div>${statusSelect("booking", b.id, b.status, BOOKING_STATUS)}</div>
        </div>`).join("")}
      </div>`).join("") : '<div class="empty">Записей нет. Запишитесь в демо барбершопа или фитнес-клуба — запись появится здесь.</div>';
  }

  // ---------- Заказы ----------
  const ORDER_FLOW = ["new", "cooking", "delivering", "done"];
  async function orders() {
    const data = await api.admin.orders({ ...siteFilter(), limit: 60 });
    $("content").innerHTML = data.items.length ? `<div class="orders">${data.items.map((o) => `
      <article class="order" data-id="order-${o.id}">
        <div class="order__head"><div><b>Заказ №${o.id}</b><br><small class="muted">${fmtDate(o.created_at)} · ${siteTag(o.site)}</small></div>
          ${statusSelect("order", o.id, o.status, ORDER_STATUS)}</div>
        <div>${esc(o.name)} · <span class="mono">${esc(o.phone)}</span><br><small class="muted">${o.mode === "pickup" ? "Самовывоз" : "🛵 " + esc(o.address)}${o.comment ? " · " + esc(o.comment) : ""}</small></div>
        <ul>${o.items.map((i) => `<li><span>${esc(i.name)} × ${i.qty}</span><span class="mono">${rub(i.price * i.qty)}</span></li>`).join("")}</ul>
        <div class="order__total"><span>Итого</span><span class="mono">${rub(o.total)}</span></div>
        ${o.status === "cancelled" ? "" : `<div class="steps">${ORDER_FLOW.map((s) => `<button data-order-step="${o.id}" data-status="${s}" class="${ORDER_FLOW.indexOf(s) <= ORDER_FLOW.indexOf(o.status) ? "on" : ""}">${ORDER_STATUS[s]}</button>`).join("")}</div>`}
      </article>`).join("")}</div>` : '<div class="empty">Заказов нет. Оформите заказ в Mini App или магазине цветов.</div>';
  }

  // ---------- Каталог ----------
  async function catalog() {
    const sites = mySites().filter((s) => api.SITES.find((x) => x.slug === s && x.catalog));
    if (!sites.length) { $("content").innerHTML = '<div class="empty">У ваших сайтов нет каталога</div>'; return; }
    const site = sites.includes(state.site) ? state.site : sites[0];
    const items = await api.admin.catalog({ site });
    $("content").innerHTML = `
      <div class="notice">Изменения сразу видны на сайте: смените цену или выключите блюдо и откройте <a href="../projects/miniapp/" target="_blank" rel="noopener" style="text-decoration:underline">Mini App</a>.</div>
      <form class="add-form panel" id="addItem"><input name="name" placeholder="Название" required aria-label="Название">
        <input name="category" placeholder="Категория" aria-label="Категория"><input name="price" type="number" min="0" placeholder="Цена" required aria-label="Цена">
        <button class="btn btn--primary">Добавить</button></form>
      <div class="table-wrap"><table class="cards"><thead><tr><th>Позиция</th><th>Категория</th><th>Цена, ₽</th><th class="center">В продаже</th><th></th></tr></thead>
      <tbody>${items.map((c) => `<tr>
        <td class="wide"><b>${esc(c.name)}</b><small>${siteTag(c.site)}</small></td><td data-label="Категория">${esc(c.category)}</td>
        <td data-label="Цена, ₽"><input class="price-input mono" type="number" min="0" value="${c.price}" data-price="${c.id}" aria-label="Цена: ${esc(c.name)}"></td>
        <td class="center" data-label="В продаже"><label class="switch"><input type="checkbox" data-active="${c.id}" ${c.active ? "checked" : ""} aria-label="В продаже: ${esc(c.name)}"><span></span></label></td>
        <td class="actions"><button class="btn btn--sm btn--danger" data-del="${c.id}" aria-label="Удалить ${esc(c.name)}">Удалить</button></td>
      </tr>`).join("")}</tbody></table></div>`;
    $("addItem").onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      await run(() => api.admin.addCatalog(site, { ref: `custom-${Date.now()}`, name: f.name.value, category: f.category.value, price: Number(f.price.value) }), "Позиция добавлена");
      catalog();
    };
  }

  // ---------- Команда ----------
  async function team() {
    const users = await api.admin.users();
    $("content").innerHTML = `
      <div class="table-wrap"><table class="cards"><thead><tr><th>Сотрудник</th><th>Роль</th><th>Доступ</th><th></th></tr></thead>
      <tbody>${users.map((u) => `<tr><td class="wide"><b>${esc(u.name)}</b><small>${esc(u.email)}</small></td><td data-label="Роль">${ROLE_NAME[u.role]}</td>
        <td data-label="Доступ">${u.sites === null ? "Все сайты" : u.sites.map(siteTag).join(" ")}</td>
        <td class="actions">${u.id === state.user.id ? '<small class="muted">это вы</small>' : `<button class="btn btn--sm btn--danger" data-remove="${u.id}">Удалить</button>`}</td></tr>`).join("")}</tbody></table></div>
      <form class="panel" id="addUser" style="display:grid;gap:12px">
        <h2>Добавить сотрудника</h2>
        <div class="add-form add-form--user">
          <input name="name" placeholder="Имя" required aria-label="Имя"><input name="email" type="email" placeholder="E-mail" required aria-label="E-mail">
          <input name="password" type="password" minlength="8" placeholder="Пароль от 8 символов" required aria-label="Пароль">
          <select name="role" aria-label="Роль"><option value="staff">Сотрудник</option><option value="admin">Администратор</option><option value="owner">Владелец</option></select>
        </div>
        <div class="chips" id="userSites" role="group" aria-label="Доступ к сайтам">${api.SITES.map((s) => `<button type="button" class="chip" data-us="${s.slug}" aria-pressed="false">${esc(s.name)}</button>`).join("")}</div>
        <small class="muted">Не выбран ни один сайт — доступ ко всем.</small>
        <div><button class="btn btn--primary">Добавить</button></div>
      </form>
      <div class="notice">Сотрудник видит только свои сайты. Сотрудник меняет статусы, администратор ещё и каталог, владелец управляет командой.</div>`;
    $("userSites").onclick = (e) => { const b = e.target.closest("[data-us]"); if (b) b.setAttribute("aria-pressed", b.getAttribute("aria-pressed") !== "true"); };
    $("addUser").onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target;
      const sites = [...f.querySelectorAll('[data-us][aria-pressed="true"]')].map((b) => b.dataset.us);
      await run(() => api.admin.addUser({ name: f.name.value, email: f.email.value, password: f.password.value, role: f.role.value, sites: sites.length ? sites : null }), "Сотрудник добавлен");
      team();
    };
  }

  // ---------- Действия в списках (делегирование) ----------
  $("content").addEventListener("change", async (e) => {
    const t = e.target;
    const d = t.dataset;
    if (d.lead) { await run(() => api.admin.updateLead(d.lead, t.value), "Статус заявки обновлён"); t.className = `status s-${t.value}`; updateBadges(); }
    if (d.booking) { await run(() => api.admin.updateBooking(d.booking, t.value), "Запись обновлена"); bookings(); }
    if (d.order) { await run(() => api.admin.updateOrder(d.order, t.value), "Статус заказа обновлён"); orders(); }
    if (d.price) { await run(() => api.admin.updateCatalog(d.price, { price: Number(t.value) }), "Цена сохранена"); }
    if (d.active) { await run(() => api.admin.updateCatalog(d.active, { active: t.checked }), t.checked ? "Снова в продаже" : "Убрано в стоп-лист"); }
  });
  $("content").addEventListener("click", async (e) => {
    const t = e.target.closest("button");
    if (!t) return;
    const d = t.dataset;
    if (d.orderStep) { await run(() => api.admin.updateOrder(d.orderStep, d.status), `Заказ: ${ORDER_STATUS[d.status].toLowerCase()}`); orders(); }
    if (d.del) {
      if (t.dataset.confirm !== "1") { t.dataset.confirm = "1"; t.textContent = "Точно?"; setTimeout(() => { t.dataset.confirm = ""; t.textContent = "Удалить"; }, 2500); return; }
      await run(() => api.admin.deleteCatalog(d.del), "Позиция удалена"); catalog();
    }
    if (d.remove) {
      if (t.dataset.confirm !== "1") { t.dataset.confirm = "1"; t.textContent = "Точно?"; setTimeout(() => { t.dataset.confirm = ""; t.textContent = "Удалить"; }, 2500); return; }
      await run(() => api.admin.removeUser(d.remove), "Сотрудник удалён"); team();
    }
  });

  // ---------- Живые обновления ----------
  async function snapshot() {
    const s = await api.admin.stats({});
    return s.leads + s.bookings + s.orders;
  }
  api.onChange(async () => {
    if (!state.user) return;
    try {
      const total = await snapshot();
      if (state.known !== null && total > state.known) toast("🔔 Новое обращение с сайта");
      state.known = total;
    } catch { /* сеть */ }
    if (["overview", "leads", "bookings", "orders"].includes(state.view)) render();
  });

  // ---------- Старт ----------
  async function start() {
    renderShell();
    state.known = await snapshot().catch(() => null);
    go(location.hash.slice(1) || "overview");
  }
  (async () => {
    state.user = await api.me().catch(() => null);
    state.user ? start() : showLogin();
  })();
})();
