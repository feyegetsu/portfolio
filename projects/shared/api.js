/*
 * Клиент API для демо-сайтов и админки.
 *
 * Два режима с одинаковым интерфейсом:
 *  - remote: запросы к бэкенду из /backend (FastAPI). Включается параметром ?api=https://адрес-api
 *            (запоминается в браузере, ?api=off возвращает демо) или переменной window.PORTFOLIO_API;
 *  - demo:   тот же контракт и те же правила (валидация, занятые слоты, цены из каталога, роли),
 *            но данные хранятся в localStorage. Так всё работает на GitHub Pages без сервера,
 *            а заявка с сайта появляется в админке, открытой в соседней вкладке, без перезагрузки.
 */
(() => {
  const SITES = [
    { slug: "cafe", name: "Кофейня «Зерно»", leads: true },
    { slug: "florist", name: "Пион & Ко", leads: true, orders: true },
    { slug: "barbershop", name: "Барбершоп BLADE", bookings: true, exclusive: true },
    { slug: "dental", name: "Стоматология «Белая линия»", leads: true },
    { slug: "fitness", name: "Фитнес-клуб PULSE", leads: true, bookings: true },
    { slug: "autoservice", name: "Автосервис «МоторЛайн»", leads: true },
    { slug: "realty", name: "Агентство «Квадрат»", leads: true },
    { slug: "saas", name: "Taskly", leads: true },
    { slug: "miniapp", name: "Сытый Лис", orders: true, catalog: true },
  ];
  const SITE = Object.fromEntries(SITES.map((s) => [s.slug, s]));
  const ROLE_LEVEL = { staff: 1, admin: 2, owner: 3 };

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  const normalizePhone = (v) => {
    const cleaned = String(v || "").replace(/[^\d+]/g, "");
    if (!/^\+?\d{10,15}$/.test(cleaned)) throw new ApiError("Некорректный номер телефона", 422);
    return cleaned;
  };

  // ---------- Выбор режима ----------
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} },
  };
  const qp = new URLSearchParams(location.search).get("api");
  if (qp === "off") store.del("pf-api");
  else if (qp) store.set("pf-api", qp.replace(/\/$/, ""));
  const BASE = (qp !== "off" && (store.get("pf-api") || window.PORTFOLIO_API)) || "";

  // =====================================================================
  // remote: настоящий бэкенд
  // =====================================================================
  function remoteApi(base) {
    const tokenKey = "pf-token";
    const token = () => { try { return sessionStorage.getItem(tokenKey); } catch { return null; } };

    async function req(method, path, body, { raw } = {}) {
      const headers = { "Content-Type": "application/json" };
      if (token()) headers.Authorization = `Bearer ${token()}`;
      let res;
      try {
        res = await fetch(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
      } catch {
        throw new ApiError("Сервер недоступен. Проверьте соединение.", 0);
      }
      if (raw && res.ok) return res;
      const data = res.status === 204 ? null : await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data && data.detail;
        const msg = Array.isArray(detail) ? detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ") : detail;
        throw new ApiError(msg || `Ошибка ${res.status}`, res.status);
      }
      return data;
    }
    const qs = (o = {}) => {
      const p = Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "");
      return p.length ? "?" + new URLSearchParams(p).toString() : "";
    };

    return {
      mode: "remote",
      base,
      createLead: (site, b) => req("POST", `/api/v1/sites/${site}/leads`, b),
      busySlots: (site, resource, date) => req("GET", `/api/v1/sites/${site}/slots${qs({ resource, date })}`),
      createBooking: (site, b) => req("POST", `/api/v1/sites/${site}/bookings`, b),
      createOrder: (site, b) => req("POST", `/api/v1/sites/${site}/orders`, b),
      orderStatus: (site, id) => req("GET", `/api/v1/sites/${site}/orders/${id}`),
      catalog: (site) => req("GET", `/api/v1/sites/${site}/catalog`),
      async login(email, password) {
        const r = await req("POST", "/api/v1/auth/login", { email, password });
        try { sessionStorage.setItem(tokenKey, r.access_token); } catch {}
        return this.me();
      },
      logout() { try { sessionStorage.removeItem(tokenKey); } catch {} },
      me: () => (token() ? req("GET", "/api/v1/auth/me") : Promise.resolve(null)),
      admin: {
        leads: (f) => req("GET", `/api/v1/admin/leads${qs(f)}`),
        updateLead: (id, status) => req("PATCH", `/api/v1/admin/leads/${id}`, { status }),
        bookings: (f) => req("GET", `/api/v1/admin/bookings${qs(f)}`),
        updateBooking: (id, status) => req("PATCH", `/api/v1/admin/bookings/${id}`, { status }),
        orders: (f) => req("GET", `/api/v1/admin/orders${qs(f)}`),
        updateOrder: (id, status) => req("PATCH", `/api/v1/admin/orders/${id}`, { status }),
        catalog: (f) => req("GET", `/api/v1/admin/catalog${qs(f)}`),
        addCatalog: (site, b) => req("POST", `/api/v1/admin/catalog/${site}`, b),
        updateCatalog: (id, b) => req("PATCH", `/api/v1/admin/catalog/item/${id}`, b),
        deleteCatalog: (id) => req("DELETE", `/api/v1/admin/catalog/item/${id}`),
        stats: (f) => req("GET", `/api/v1/admin/stats${qs(f)}`),
        users: () => req("GET", "/api/v1/admin/users"),
        addUser: (b) => req("POST", "/api/v1/admin/users", b),
        removeUser: (id) => req("DELETE", `/api/v1/admin/users/${id}`),
        exportLeads: async (f) => (await req("GET", `/api/v1/admin/leads.csv${qs(f)}`, null, { raw: true })).text(),
      },
      // Удалённые изменения подтягиваем опросом раз в 15 секунд
      onChange(cb) { const t = setInterval(cb, 15000); return () => clearInterval(t); },
    };
  }

  // =====================================================================
  // demo: тот же контракт поверх localStorage
  // =====================================================================
  function demoApi() {
    const KEY = "pf-db-v1";
    const SESSION = "pf-demo-user";
    const now = () => new Date();
    const iso = (d) => new Date(d).toISOString();
    const pad = (n) => String(n).padStart(2, "0");
    const localIso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;

    function seedData() {
      const db = { seq: 1, users: [], leads: [], bookings: [], orders: [], catalog: [] };
      const id = () => db.seq++;
      const ago = (days, h = 12, m = 0) => { const d = now(); d.setDate(d.getDate() - days); d.setHours(h, m, 0, 0); return iso(d); };
      db.users.push(
        { id: id(), email: "demo@feyegetsu.dev", password: "demo", name: "Владелец (демо)", role: "owner", sites: null },
        { id: id(), email: "cafe@feyegetsu.dev", password: "demo", name: "Администратор кофейни", role: "staff", sites: ["cafe"] },
      );
      const leads = [
        ["cafe", "table", "Анна Смирнова", "+79161234567", "Столик у окна, будет торт", { date: "", time: "19:00", guests: "4" }, 0, "new"],
        ["dental", "consult", "Игорь Петров", "+79035550101", "Ноет зуб мудрости", { doctor: "Михаил Орлов" }, 0, "new"],
        ["realty", "viewing", "Ольга Ким", "+79260002233", "", { object: "2-комнатная, ЖК «Парк Авеню»" }, 1, "in_progress"],
        ["autoservice", "repair", "Денис Волков", "+79857771122", "Toyota Camry", { works: ["Замена масла", "Диагностика"], total: 2700 }, 1, "new"],
        ["saas", "signup", "", "", "", { email: "team@startup.io" }, 2, "done"],
        ["dental", "quiz", "", "+79031112233", "", { result: "Отбеливание или виниры", range: "24 000 – 120 000 ₽" }, 3, "in_progress"],
        ["cafe", "table", "Михаил Орлов", "+79167778899", "", { time: "12:00", guests: "2" }, 4, "done"],
        ["fitness", "trial", "Екатерина Лис", "+79991234455", "", {}, 5, "done"],
        ["florist", "subscribe", "", "", "", { email: "lena@mail.ru" }, 6, "done"],
        ["realty", "viewing", "Павел Лебедев", "+79095556677", "", { object: "Студия, ул. Садовая, 14" }, 8, "cancelled"],
      ];
      leads.forEach(([site, kind, name, phone, message, data, days, status], i) => {
        db.leads.push({ id: id(), site, kind, name, phone, email: data.email || "", message, data, status, created_at: ago(days, 9 + ((i * 5) % 11), 15) });
      });
      const tomorrow = now(); tomorrow.setDate(tomorrow.getDate() + 1);
      const at = (h) => { const d = new Date(tomorrow); d.setHours(h, 0, 0, 0); return localIso(d); };
      db.bookings.push(
        { id: id(), site: "barbershop", resource: "Артём", service: "Мужская стрижка", starts_at: at(12), name: "Сергей", phone: "+79161112233", status: "confirmed", created_at: ago(0, 9) },
        { id: id(), site: "barbershop", resource: "Денис", service: "Стрижка + борода", starts_at: at(17), name: "Алексей", phone: "+79262223344", status: "confirmed", created_at: ago(1, 18) },
        { id: id(), site: "fitness", resource: "Кроссфит", service: "18:00", starts_at: at(18), name: "Марина", phone: "+79853334455", status: "confirmed", created_at: ago(2, 20) },
      );
      db.orders.push(
        { id: id(), site: "miniapp", items: [{ ref: "1", name: "Маргарита", qty: 2, price: 549 }, { ref: "16", name: "Лимонады", qty: 2, price: 219 }], total: 1536, name: "Никита", phone: "+79031234567", address: "ул. Ленина, 5, кв. 12", mode: "delivery", comment: "", status: "delivering", created_at: ago(0, 13, 40) },
        { id: id(), site: "florist", items: [{ ref: "1", name: "Утренний сад", qty: 1, price: 4900 }], total: 4900, name: "Виктория", phone: "+79165554433", address: "пр. Мира, 7", mode: "delivery", comment: "Позвонить за час", status: "new", created_at: ago(0, 11, 5) },
        { id: id(), site: "miniapp", items: [{ ref: "9", name: "Сет «Лис»", qty: 1, price: 1590 }], total: 1590, name: "Ирина", phone: "+79267778899", address: "", mode: "pickup", comment: "", status: "done", created_at: ago(1, 19, 20) },
        { id: id(), site: "florist", items: [{ ref: "3", name: "Классика", qty: 1, price: 8900 }], total: 8900, name: "Артур", phone: "+79998887766", address: "ул. Цветочная, 22", mode: "delivery", comment: "", status: "done", created_at: ago(3, 15) },
      );
      const menu = [["1", "Маргарита", "Пицца", 549], ["2", "Пепперони", "Пицца", 649], ["3", "Овощная", "Пицца", 599], ["4", "Четыре сезона", "Пицца", 699],
        ["5", "Классик", "Бургеры", 429], ["6", "Пулд-порк", "Бургеры", 469], ["7", "Бургер + фри", "Бургеры", 549], ["8", "Филадельфия", "Роллы", 589],
        ["9", "Сет «Лис»", "Роллы", 1590], ["10", "Нигири микс", "Роллы", 690], ["11", "Боул с курицей", "Боулы", 459], ["12", "Поке с лососем", "Боулы", 549],
        ["13", "Паста с морепродуктами", "Горячее", 589], ["14", "Пенне арабьята", "Горячее", 399], ["15", "Стейк с фри", "Горячее", 890], ["16", "Лимонады", "Напитки", 219]];
      for (const [ref, name, category, price] of menu) db.catalog.push({ id: id(), site: "miniapp", ref, name, category, price, active: true });
      return db;
    }

    function load() {
      try { const raw = store.get(KEY); if (raw) return JSON.parse(raw); } catch {}
      const db = seedData();
      save(db);
      return db;
    }
    function save(db) { store.set(KEY, JSON.stringify(db)); }
    // Маленькая задержка, как у сети: интерфейс честно показывает состояние «отправляется»
    const later = (fn) => new Promise((resolve, reject) => setTimeout(() => { try { resolve(fn()); } catch (e) { reject(e); } }, 250));
    const site = (slug, flag) => {
      const s = SITE[slug];
      if (!s) throw new ApiError("Сайт не найден", 404);
      if (flag && !s[flag]) throw new ApiError("Этот сайт так не умеет", 404);
      return s;
    };
    const clone = (o) => JSON.parse(JSON.stringify(o));

    // ---------- сессия и права ----------
    function user() {
      const id = Number(store.get(SESSION));
      return id ? load().users.find((u) => u.id === id) || null : null;
    }
    function requireUser(minRole = "staff") {
      const u = user();
      if (!u) throw new ApiError("Нужно войти", 401);
      if (ROLE_LEVEL[u.role] < ROLE_LEVEL[minRole]) throw new ApiError("Недостаточно прав", 403);
      return u;
    }
    const allowed = (u) => (u.sites === null ? SITES.map((s) => s.slug) : u.sites);
    function scoped(list, u, siteFilter) {
      const sites = allowed(u);
      if (siteFilter && !sites.includes(siteFilter)) throw new ApiError("Нет доступа к этому сайту", 403);
      return list.filter((x) => (siteFilter ? x.site === siteFilter : sites.includes(x.site)));
    }
    const page = (list, { limit = 50, offset = 0 } = {}) => {
      const sorted = [...list].sort((a, b) => (a.created_at < b.created_at ? 1 : -1) || b.id - a.id);
      return { items: clone(sorted.slice(Number(offset), Number(offset) + Number(limit))), total: list.length };
    };
    const publicUser = (u) => ({ id: u.id, email: u.email, name: u.name, role: u.role, sites: u.sites });

    function patch(collection, id, changes, u) {
      const db = load();
      const item = db[collection].find((x) => x.id === Number(id));
      if (!item) throw new ApiError("Не найдено", 404);
      if (!allowed(u).includes(item.site)) throw new ApiError("Нет доступа к этому сайту", 403);
      Object.assign(item, changes);
      save(db);
      return clone(item);
    }

    const LEAD_STATUSES = ["new", "in_progress", "done", "cancelled"];
    const BOOKING_STATUSES = ["confirmed", "done", "cancelled"];
    const ORDER_STATUSES = ["new", "cooking", "delivering", "done", "cancelled"];
    const checkStatus = (s, list) => { if (!list.includes(s)) throw new ApiError("Неизвестный статус", 422); };

    return {
      mode: "demo",
      base: "",
      createLead: (slug, b) => later(() => {
        site(slug, "leads");
        const phone = b.phone ? normalizePhone(b.phone) : "";
        if (!phone && !b.email) throw new ApiError("Укажите телефон или e-mail", 422);
        const db = load();
        const lead = { id: db.seq++, site: slug, kind: b.kind, name: b.name || "", phone, email: b.email || "", message: b.message || "", data: b.data || {}, status: "new", created_at: iso(now()) };
        db.leads.push(lead);
        save(db);
        return { id: lead.id, status: lead.status };
      }),
      busySlots: (slug, resource, date) => later(() => {
        site(slug, "bookings");
        return load().bookings
          .filter((b) => b.site === slug && b.resource === resource && b.status !== "cancelled" && b.starts_at.slice(0, 10) === date)
          .map((b) => b.starts_at.slice(11, 16));
      }),
      createBooking: (slug, b) => later(() => {
        const s = site(slug, "bookings");
        const phone = normalizePhone(b.phone);
        if (!b.name) throw new ApiError("Укажите имя", 422);
        const startsAt = String(b.starts_at).slice(0, 16) + ":00";
        if (new Date(startsAt) < new Date(Date.now() - 5 * 60000)) throw new ApiError("Это время уже прошло", 422);
        const db = load();
        if (s.exclusive && db.bookings.some((x) => x.site === slug && x.resource === b.resource && x.starts_at === startsAt && x.status !== "cancelled")) {
          throw new ApiError("Это время уже заняли, выберите другое", 409);
        }
        const booking = { id: db.seq++, site: slug, resource: b.resource, service: b.service || "", starts_at: startsAt, name: b.name, phone, status: "confirmed", created_at: iso(now()) };
        db.bookings.push(booking);
        save(db);
        return { id: booking.id, status: booking.status };
      }),
      createOrder: (slug, b) => later(() => {
        const s = site(slug, "orders");
        const phone = normalizePhone(b.phone);
        if (!b.items || !b.items.length) throw new ApiError("Корзина пуста", 422);
        if ((b.mode || "delivery") === "delivery" && !String(b.address || "").trim()) throw new ApiError("Укажите адрес доставки", 422);
        const db = load();
        const items = clone(b.items);
        if (s.catalog) {
          // ref «1» — позиция как в каталоге, «1:2:0» — с модификаторами (размер, добавки): наличие проверяем по базовой позиции
          for (const item of items) {
            const ref = String(item.ref || "");
            const base = db.catalog.find((c) => c.site === slug && c.ref === ref.split(":")[0]);
            if (base && !base.active) throw new ApiError(`«${base.name}» закончилось`, 409);
            if (base && base.ref === ref) item.price = base.price;
          }
        }
        const order = { id: db.seq++, site: slug, items, total: items.reduce((t, i) => t + i.price * i.qty, 0), name: b.name, phone, address: b.address || "", mode: b.mode || "delivery", comment: b.comment || "", status: "new", created_at: iso(now()) };
        db.orders.push(order);
        save(db);
        return { id: order.id, status: order.status };
      }),
      orderStatus: (slug, id) => later(() => {
        const o = load().orders.find((x) => x.id === Number(id) && x.site === slug);
        if (!o) throw new ApiError("Заказ не найден", 404);
        return { id: o.id, status: o.status, total: o.total };
      }),
      catalog: (slug) => later(() => { site(slug, "catalog"); return clone(load().catalog.filter((c) => c.site === slug)); }),

      login: (email, password) => later(() => {
        const u = load().users.find((x) => x.email === String(email).trim().toLowerCase() && x.password === password);
        if (!u) throw new ApiError("Неверный e-mail или пароль", 401);
        store.set(SESSION, String(u.id));
        return publicUser(u);
      }),
      logout() { store.del(SESSION); },
      me: () => later(() => { const u = user(); return u ? publicUser(u) : null; }),

      admin: {
        leads: (f = {}) => later(() => {
          let list = scoped(load().leads, requireUser(), f.site);
          if (f.status) list = list.filter((l) => l.status === f.status);
          if (f.q) {
            const q = f.q.trim().toLowerCase();
            list = list.filter((l) => [l.name, l.phone, l.email, l.message].join(" ").toLowerCase().includes(q));
          }
          return page(list, f);
        }),
        updateLead: (id, status) => later(() => { checkStatus(status, LEAD_STATUSES); return patch("leads", id, { status }, requireUser()); }),
        bookings: (f = {}) => later(() => {
          let list = scoped(load().bookings, requireUser(), f.site);
          if (f.upcoming) list = list.filter((b) => b.status === "confirmed" && new Date(b.starts_at) > new Date(Date.now() - 12 * 3600e3));
          return page(list, f);
        }),
        updateBooking: (id, status) => later(() => { checkStatus(status, BOOKING_STATUSES); return patch("bookings", id, { status }, requireUser()); }),
        orders: (f = {}) => later(() => {
          let list = scoped(load().orders, requireUser(), f.site);
          if (f.status) list = list.filter((o) => o.status === f.status);
          return page(list, f);
        }),
        updateOrder: (id, status) => later(() => { checkStatus(status, ORDER_STATUSES); return patch("orders", id, { status, touched: true }, requireUser()); }),
        catalog: (f = {}) => later(() => clone(scoped(load().catalog, requireUser(), f.site))),
        addCatalog: (slug, b) => later(() => {
          const u = requireUser("admin");
          site(slug, "catalog");
          if (!allowed(u).includes(slug)) throw new ApiError("Нет доступа к этому сайту", 403);
          const db = load();
          const item = { id: db.seq++, site: slug, ref: b.ref, name: b.name, category: b.category || "", price: Number(b.price), active: b.active !== false };
          db.catalog.push(item);
          save(db);
          return clone(item);
        }),
        updateCatalog: (id, b) => later(() => {
          const changes = {};
          if (b.name !== undefined) changes.name = b.name;
          if (b.price !== undefined) {
            if (!(Number(b.price) >= 0)) throw new ApiError("Цена должна быть числом", 422);
            changes.price = Number(b.price);
          }
          if (b.active !== undefined) changes.active = !!b.active;
          return patch("catalog", id, changes, requireUser("admin"));
        }),
        deleteCatalog: (id) => later(() => {
          const u = requireUser("admin");
          const db = load();
          const item = db.catalog.find((c) => c.id === Number(id));
          if (!item) throw new ApiError("Не найдено", 404);
          if (!allowed(u).includes(item.site)) throw new ApiError("Нет доступа к этому сайту", 403);
          db.catalog = db.catalog.filter((c) => c !== item);
          save(db);
          return null;
        }),
        stats: (f = {}) => later(() => {
          const u = requireUser();
          const db = load();
          const leads = scoped(db.leads, u, f.site), bookings = scoped(db.bookings, u, f.site), orders = scoped(db.orders, u, f.site);
          const days = Number(f.days || 14);
          const byDay = {};
          for (let i = days - 1; i >= 0; i--) { const d = now(); d.setDate(d.getDate() - i); byDay[d.toISOString().slice(0, 10)] = 0; }
          const bySite = {};
          for (const x of [...leads, ...bookings, ...orders]) {
            const k = x.created_at.slice(0, 10);
            if (k in byDay) byDay[k]++;
            bySite[x.site] = (bySite[x.site] || 0) + 1;
          }
          return {
            leads: leads.length, bookings: bookings.length, orders: orders.length,
            revenue: orders.filter((o) => o.status !== "cancelled").reduce((t, o) => t + o.total, 0),
            new_leads: leads.filter((l) => l.status === "new").length,
            by_day: Object.entries(byDay).map(([date, count]) => ({ date, count })),
            by_site: bySite,
          };
        }),
        users: () => later(() => { requireUser("owner"); return load().users.map(publicUser); }),
        addUser: (b) => later(() => {
          requireUser("owner");
          if (!b.email || !b.name || !b.password || b.password.length < 8) throw new ApiError("Заполните e-mail, имя и пароль от 8 символов", 422);
          const db = load();
          const email = b.email.trim().toLowerCase();
          if (db.users.some((u) => u.email === email)) throw new ApiError("Пользователь с таким e-mail уже есть", 409);
          const u = { id: db.seq++, email, name: b.name, password: b.password, role: b.role || "staff", sites: b.sites ?? null };
          db.users.push(u);
          save(db);
          return publicUser(u);
        }),
        removeUser: (id) => later(() => {
          const me = requireUser("owner");
          if (Number(id) === me.id) throw new ApiError("Нельзя удалить самого себя", 422);
          const db = load();
          db.users = db.users.filter((u) => u.id !== Number(id));
          save(db);
          return null;
        }),
        exportLeads: (f = {}) => later(() => {
          const rows = scoped(load().leads, requireUser(), f.site).sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
          const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
          const lines = [["id", "Дата", "Сайт", "Тип", "Имя", "Телефон", "E-mail", "Комментарий", "Статус"].join(";")];
          for (const r of rows) lines.push([r.id, new Date(r.created_at).toLocaleString("ru-RU"), SITE[r.site].name, r.kind, r.name, r.phone, r.email, r.message, r.status].map(cell).join(";"));
          return "﻿" + lines.join("\n");
        }),
      },

      // Изменения из других вкладок приходят через событие storage
      onChange(cb) {
        const h = (e) => { if (e.key === KEY) cb(); };
        addEventListener("storage", h);
        return () => removeEventListener("storage", h);
      },
      // Только для демо: «кухня» сама двигает заказ, пока его статус не поменяли руками в админке
      demoAdvanceOrder(id, next) {
        const db = load();
        const o = db.orders.find((x) => x.id === Number(id));
        if (!o || o.touched || o.status === "done" || o.status === "cancelled") return;
        o.status = next;
        save(db);
      },
      reset() { store.del(KEY); store.del(SESSION); load(); },
    };
  }

  const api = BASE ? remoteApi(BASE) : demoApi();
  api.SITES = SITES;
  api.ApiError = ApiError;

  // ---------- Помощники для форм на сайтах ----------

  // Блокирует кнопку на время отправки и показывает ошибку под ней. Ошибку пробрасывает дальше.
  api.submit = async (form, fn) => {
    const btn = form.querySelector('button[type="submit"], button:not([type])');
    let err = form.querySelector(".pf-error");
    if (!err) {
      err = Object.assign(document.createElement("p"), { className: "pf-error" });
      err.setAttribute("role", "alert");
      err.style.cssText = "color:#d92d20;font-size:14px;margin:6px 0 0;font-weight:500";
      (btn || form.lastElementChild).insertAdjacentElement("afterend", err);
    }
    err.textContent = "";
    const label = btn && btn.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "Отправляем…"; }
    try {
      return await fn();
    } catch (e) {
      err.textContent = e.message || "Не удалось отправить";
      throw e;
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = label; }
    }
  };

  // Ссылка «посмотреть в админке» под сообщением об успехе (только в демо)
  api.adminLink = (view = "leads", root = "../../") => api.mode === "demo"
    ? `<a href="${root}admin/#${view}" target="_blank" rel="noopener" style="display:inline-block;margin-top:10px;color:inherit;text-decoration:underline;font-weight:600">Посмотреть в админке →</a>`
    : "";

  // Спрашивает имя и телефон в небольшом окне, запоминает их для следующих записей
  api.askContact = (title = "Ваши контакты") => new Promise((resolve, reject) => {
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem("pf-contact")) || {}; } catch {}
    const dlg = document.createElement("dialog");
    dlg.style.cssText = "border:0;border-radius:18px;padding:24px;width:min(360px,calc(100% - 32px));font:15px system-ui,sans-serif;color:#111;box-shadow:0 30px 80px rgba(0,0,0,.4)";
    dlg.innerHTML = `<form method="dialog" style="display:grid;gap:12px">
      <b style="font-size:18px">${title}</b>
      <input name="name" required placeholder="Имя" autocomplete="name" style="padding:12px;border:1px solid #ccc;border-radius:10px;font:inherit">
      <input name="phone" type="tel" required placeholder="Телефон" autocomplete="tel" style="padding:12px;border:1px solid #ccc;border-radius:10px;font:inherit">
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button value="cancel" formnovalidate style="padding:10px 16px;border-radius:10px;border:1px solid #ccc;background:#fff;font:inherit;cursor:pointer">Отмена</button>
        <button value="ok" style="padding:10px 16px;border-radius:10px;border:0;background:#111;color:#fff;font:inherit;font-weight:600;cursor:pointer">Продолжить</button>
      </div></form>`;
    document.body.appendChild(dlg);
    const f = dlg.querySelector("form");
    f.elements.name.value = saved.name || "";
    f.elements.phone.value = saved.phone || "";
    // Завершаем по отправке формы и по Esc, не дожидаясь события close: в фоновых вкладках оно может запаздывать
    let finished = false;
    const finish = (ok) => {
      if (finished) return;
      finished = true;
      const contact = { name: f.elements.name.value.trim(), phone: f.elements.phone.value.trim() };
      if (dlg.open) dlg.close();
      dlg.remove();
      if (!ok) return reject(new ApiError("Отменено", 0));
      try { localStorage.setItem("pf-contact", JSON.stringify(contact)); } catch {}
      resolve(contact);
    };
    f.addEventListener("submit", (e) => { e.preventDefault(); finish(!e.submitter || e.submitter.value === "ok"); });
    dlg.addEventListener("cancel", (e) => { e.preventDefault(); finish(false); });
    dlg.addEventListener("close", () => finish(dlg.returnValue === "ok"));
    dlg.showModal();
  });

  window.PortfolioAPI = api;
})();
